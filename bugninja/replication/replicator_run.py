"""
Browser Interaction ReplicatorRun

This module implements a class that can read and execute browser interactions
from a JSON log file. It processes each interaction sequentially and performs the
corresponding browser actions using Patchright (undetected Playwright).

The JSON log file contains steps with:
- model_taken_action: The action to perform
- interacted_element: Details about the element to interact with
- brain: Agent's reasoning and state
- action_details: Specific details about the action

The replication process includes a free healing mechanism that allows the healing
agent to take over completely when a replay action fails, running through the
entire remaining traversal without stopping for state matching or brain state
boundaries.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

from cuid2 import Cuid as CUID
from rich import print as rich_print

from bugninja.agents.healer_agent import HealerAgent
from bugninja.config import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)
from bugninja.config.llm_config import LLMConfig
from bugninja.events import EventPublisherManager
from bugninja.replication.errors import ReplicatorError
from bugninja.replication.replicator_navigation import (
    ReplicatorNavigator,
    get_user_input,
)
from bugninja.schemas.pipeline import (
    BugninjaBrainState,
    BugninjaExtendedAction,
    ReplayWithHealingStateMachine,
    Traversal,
)
from bugninja.utils.logger_config import set_logger_config
from bugninja.utils.screenshot_manager import ScreenshotManager

# Configure logging with custom format
set_logger_config()
logger = logging.getLogger(__name__)


class UserInterruptionError(ReplicatorError):
    """Exception raised when user interrupts the replication process."""

    pass


class ReplicatorRun(ReplicatorNavigator):
    """
    A class that replicates browser interactions from a JSON log file.

    This class reads a JSON file containing browser interaction steps and
    executes them sequentially using Patchright. Each interaction is processed
    and the corresponding browser action is performed with fallback mechanisms
    for element selection.
    """

    def __init__(
        self,
        traversal_source: Union[str, Traversal],
        run_id: Optional[str] = None,
        fail_on_unimplemented_action: bool = False,
        sleep_after_actions: float = 1.0,
        pause_after_each_step: bool = True,
        enable_healing: bool = True,
        event_manager: Optional[EventPublisherManager] = None,
        background: bool = False,
        healing_llm_config: Optional[LLMConfig] = None,
    ):
        """
        Initialize the ReplicatorRun with a JSON file path or Traversal object.

        Args:
            traversal_source: Path to the JSON file containing interaction steps or Traversal object
            fail_on_unimplemented_action: Whether to fail on unimplemented actions
            sleep_after_actions: Time to sleep after each action
            pause_after_each_step: Whether to pause and wait for Enter key after each step
            enable_healing: Whether to enable healing when actions fail (default: True)
            event_manager: Optional event publisher manager for tracking
            background: Whether to run in background mode (disables console logging)
            healing_llm_config: Optional LLM configuration for healing agent (uses default if None)
        """

        super().__init__(
            traversal_source=traversal_source,
            fail_on_unimplemented_action=fail_on_unimplemented_action,
            sleep_after_actions=sleep_after_actions,
            background=background,
        )

        # Store the original source for metadata and error reporting
        self.traversal_source = traversal_source

        # Determine the traversal path for file-based operations
        if isinstance(traversal_source, str):
            self.traversal_path = traversal_source
        else:
            # For Traversal objects, we don't have a file path, so we'll use a placeholder
            # This is mainly used for error reporting and metadata
            self.traversal_path = "traversal_object"

        self.max_retries = 2
        self.retry_delay = 0.5

        self.healing_happened = False
        self._traversal: Optional[Traversal] = None  # Store traversal after successful run

        self.pause_after_each_step = pause_after_each_step
        self.enable_healing = enable_healing
        self.healing_llm_config: Optional[LLMConfig] = healing_llm_config
        self.secrets = self.replay_traversal.secrets

        # Get the number of actions from the actions dictionary
        self.total_actions = len(self.replay_traversal.actions)

        # Generate run_id at creation time for consistency
        self.run_id: str = CUID().generate()

        if run_id is not None:
            self.run_id = run_id

        # Initialize screenshot manager
        self.screenshot_manager = ScreenshotManager(run_id=self.run_id, folder_prefix="replay")

        # Initialize event publisher manager (explicitly passed)
        self.event_manager = event_manager

        brain_state_list: List[BugninjaBrainState] = [
            BugninjaBrainState(
                id=i,
                evaluation_previous_goal=bs.evaluation_previous_goal,
                memory=bs.memory,
                next_goal=bs.next_goal,
            )
            for i, bs in self.replay_traversal.brain_states.items()
        ]

        replay_action_list: List[BugninjaExtendedAction] = list(
            self.replay_traversal.actions.values()
        )

        self.replay_state_machine = ReplayWithHealingStateMachine(
            current_action=replay_action_list[0],
            current_brain_state=brain_state_list[0],
            replay_states=brain_state_list[1:],
            replay_actions=replay_action_list[1:],
        )

        self._log_if_not_background(
            "info", f"🚀 Initialized ReplicatorRun with {self.total_actions} steps to process"
        )
        if self.pause_after_each_step:
            self._log_if_not_background(
                "info",
                "⏸️ Pause after each step is ENABLED - press Enter to continue after each action",
            )
        self._log_if_not_background(
            "info",
            f"📸 Screenshots will be saved to: {self.screenshot_manager.get_screenshots_dir()}",
        )

    def _wait_for_enter_key(self) -> None:
        """
        Wait for the user to press the Enter key to continue.

        This method provides a pause mechanism that allows users to review
        each step before proceeding to the next one.
        """
        try:
            user_input: str = get_user_input()
            if user_input == "q":
                raise UserInterruptionError("User interrupted the replication process")
            logger.info("▶️ Continuing to next step...")
        except UserInterruptionError:
            logger.warning("⚠️ Interrupted by user ('q' pressed)")
            raise UserInterruptionError("User interrupted the replication process")
        except Exception as e:
            logger.error(f"❌ Unexpected error waiting for user input: {str(e)}")
            # Continue anyway to avoid blocking the process
            logger.info("▶️ Continuing to next step...")

    async def create_self_healing_agent(self) -> HealerAgent:
        """
        Start the self-healing agent.
        """
        # Use provided LLM config or fall back to default
        if self.healing_llm_config:
            llm = create_llm_model_from_config(self.healing_llm_config)
            logger.info(
                f"🩹 Using custom LLM for healing: {self.healing_llm_config.provider.value} - {self.healing_llm_config.model}"
            )
        else:
            llm = create_llm_model_from_config(create_llm_config_from_settings())
            logger.info("🩹 Using default LLM configuration for healing")

        agent = HealerAgent(
            task=self.replay_traversal.test_case,
            llm=llm,
            browser_session=self.browser_session,
            sensitive_data=self.secrets,
            parent_run_id=self.run_id,  # Pass parent's run_id to maintain consistency
            # TODO! experiment with adding the proper state from previous runs for the brain to be aware what is happening
            # injected_agent_state=self.create_agent_state_from_traversal_json(cut_after=at_idx),
        )

        # Share screenshot directory and counter with healing agent
        agent.screenshot_manager = self.screenshot_manager

        await agent._before_run_hook()

        return agent

    def _save_corrected_traversal(self, output_path: Optional[str] = None) -> Traversal:
        """
        Save the corrected traversal containing successful actions and healer replacements.

        Args:
            output_path: Optional path to save the corrected traversal. If None and source is a file,
                        will append "_corrected" to the original filename.

        Returns:
            Traversal: The corrected traversal object
        """
        logger.info("💾 Building corrected traversal with healer actions...")

        # overwrite the actions
        self.replay_traversal.brain_states = {
            bs.id: bs.to_agent_brain() for bs in self.replay_state_machine.passed_brain_states
        }
        self.replay_traversal.actions = {
            f"action_{i}": e for i, e in enumerate(self.replay_state_machine.passed_actions)
        }

        # Determine output path
        if output_path is None:
            if isinstance(self.traversal_source, str):
                # For file-based sources, append "_corrected" to the original filename
                output_path = self.traversal_source.replace(".json", "_corrected.json")
            else:
                # For Traversal objects, use a default path
                output_path = f"traversal_corrected_{self.run_id}.json"

        # Save to file if we have a valid path
        if output_path and output_path != "traversal_object":
            with open(output_path, "w") as f:
                json.dump(
                    self.replay_traversal.model_dump(),
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
            logger.info(f"💾 Corrected traversal saved to: {output_path}")
        else:
            logger.info("💾 Corrected traversal built (not saved to file)")

        # Store the traversal object for later access
        self._traversal = self.replay_traversal

        return self.replay_traversal

    async def _run(self) -> Tuple[bool, Optional[str]]:
        failed = False
        failed_reason: Optional[str] = None

        logger.info("🚀 Starting replication with brain state-based processing")
        logger.info(
            f"📊 Total brain states to process: {len(self.replay_state_machine.replay_states)+1}"
        )

        # Initialize event tracking for replay run
        if self.event_manager and self.event_manager.has_publishers():
            try:
                await self.event_manager.initialize_run(
                    run_type="replay",
                    metadata={
                        "traversal_file": self.traversal_path,
                        "total_actions": self.total_actions,
                        "task_description": "Replay traversal",
                    },
                    existing_run_id=self.run_id,  # Use existing run_id instead of generating new one
                )
                logger.info(f"🎯 Started replay run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

        # ? we go until the self healing state is not finished

        agent_reached_goal: bool = False

        # Process brain states sequentially
        while not self.replay_state_machine.replay_should_stop(
            healing_agent_reached_goal=agent_reached_goal
        ):

            # Log action details
            action = self.replay_state_machine.current_action
            action_type: str = [k for k, a in action.action.items() if a is not None][0]

            logger.info("")
            logger.info(f"🔄 === PROCESSING ACTION {action_type} ===")
            logger.info(f"📋 Action type: {action_type}")

            if action_type == "click":
                element_info = action.dom_element_data
                if element_info:
                    logger.info(
                        f"🎯 Clicking element: {element_info.get('tag_name', 'Unknown')} with text: '{element_info.get('text', 'N/A')[:50]}...'"
                    )
            elif action_type == "input_text":
                text = action.action.get("input_text", {}).get("text", "")
                logger.info(f"⌨️ Inputting text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            elif action_type == "go_to_url":
                url = action.action.get("go_to_url", {}).get("url", "")
                logger.info(f"🌐 Navigating to URL: {url}")
            else:
                logger.info(f"⚙️ Performing action: {action_type}")

            try:
                logger.info("▶️ Executing action...")
                await self._execute_action(action)

                # Take screenshot after action execution
                screenshot_filename = await self._take_screenshot(action_type)
                logger.info(f"📸 Screenshot saved: {screenshot_filename}")

                logger.info("✅ Action executed successfully")

                # ? we update the state machine here that a replay action has been taken
                self.replay_state_machine.replay_action_done()

                # TODO! reenable this when action handling is properly implemented
                # # Publish action completion event
                # if self.event_manager and self.run_id:
                #     await self._publish_run_event(
                #         EventType.ACTION_COMPLETED,
                #         {
                #             "action_index": self._get_current_action_index(),
                #             "action_type": action_type,
                #             "success": True,
                #         },
                #     )

                # Add pause after action if enabled
                if self.pause_after_each_step:
                    self._wait_for_enter_key()

            except UserInterruptionError as e:
                logger.info("⏹️ User interrupted replication process")
                failed = True
                failed_reason = str(e)
                break

            except Exception as e:
                logger.error("")
                logger.error(f"❌ === ACTION '{action_type}' FAILED ===")
                logger.error(f"🚨 Error type: {type(e).__name__}")
                logger.error(f"🚨 Error message: {str(e)}")
                logger.error(
                    f"🧠 Failed in brain state: {self.replay_state_machine.current_brain_state}"
                )

                if self.enable_healing:
                    logger.info(
                        "🩹 Starting free healing agent to complete entire remaining traversal..."
                    )

                    try:

                        # Use free healing agent to complete the entire remaining traversal
                        agent_reached_goal, healer_agent = await self._start_free_healing()

                        if agent_reached_goal:
                            self.healing_happened = True
                            logger.info("✅ === HEALING AGENT REACHED GOAL ===")

                            # Replace remaining replay actions with healing actions
                            self._replace_remaining_with_healing_actions(healer_agent)

                            logger.info("🎉 === FREE HEALING COMPLETED SUCCESSFULLY ===")

                        else:
                            logger.error("❌ === FREE HEALING TIMED OUT ===")

                            failed = True
                            failed_reason = "Free healing failed to complete traversal"

                            break

                    except UserInterruptionError as e:
                        logger.info("⏹️ User interrupted the healing process")
                        failed = True
                        failed_reason = str(e)
                        break
                else:
                    # Healing is disabled, fail immediately
                    logger.error("❌ === HEALING DISABLED - REPLICATION FAILED ===")
                    failed = True
                    failed_reason = (
                        f"Action '{action_type}' failed and healing is disabled: {str(e)}"
                    )
                    break

        logger.info("")
        logger.info("🏁 === REPLICATION COMPLETED ===")
        logger.info(f"📊 Final status: {'❌ FAILED' if failed else '✅ SUCCESS'}")
        if failed:
            logger.info(f"🚨 Failure reason: {failed_reason}")

        # Save corrected traversal if healing happened (regardless of final status)
        if self.healing_happened:
            logger.info("💾 Saving corrected traversal...")
            self._save_corrected_traversal()
        else:
            # Store the original traversal if no healing occurred
            self._traversal = self.replay_traversal
            logger.warning("⚠️ No healing occurred - using original traversal")

        return not failed, failed_reason

    async def _start_free_healing(self) -> Tuple[bool, HealerAgent]:
        """
        Start the healing agent and let it run freely through the entire remaining traversal.

        This method allows the healing agent to take over completely and run through
        all remaining actions without stopping for state matching or brain state boundaries.

        Returns:
            True if healing agent completed the entire traversal successfully, False otherwise
        """
        logger.info("🩹 === STARTING FREE HEALING MODE ===")
        logger.info("🔄 Healing agent will run through entire remaining traversal")

        # Create healer agent
        healer_agent = await self.create_self_healing_agent()

        max_healing_steps = 50  # Increased limit for full traversal healing
        logger.info(f"🔄 Starting free healing loop (max {max_healing_steps} steps)")

        for i in range(max_healing_steps):
            logger.info(f"🩹 === FREE HEALER STEP #{i+1}/{max_healing_steps} ===")

            # Execute healer step
            try:
                await healer_agent.step()
            except Exception as e:
                logger.error(f"❌ Healer step failed: {str(e)}")
                return False, healer_agent

            if not healer_agent.agent_taken_actions:
                rich_print(healer_agent.agent_taken_actions)
                logger.error("❌ Healer agent failed to take any actions")
                return False, healer_agent

            # Check if healer agent has reached the goal
            try:

                # Check if we've reached a completion state (this is a simplified check)
                # In a real implementation, you might check against the original test case's expected final state
                if healer_agent.agent_taken_actions[-1].action.get("done") is not None:
                    logger.info("✅ === HEALING AGENT REACHED GOAL ===")

                    # Replace remaining replay actions with healing actions
                    self._replace_remaining_with_healing_actions(healer_agent)

                    logger.info("🎉 === FREE HEALING COMPLETED SUCCESSFULLY ===")
                    logger.info("📊 Final Summary:")
                    logger.info(f"   - Total healing steps: {i+1}")

                    return True, healer_agent

            except Exception as goal_check_error:
                logger.warning(f"⚠️ Goal detection failed: {str(goal_check_error)} - continuing")

        logger.error("❌ === FREE HEALING TIMED OUT ===")
        logger.error(f"🚨 Reached maximum steps ({max_healing_steps}) without completing goal")
        return False, healer_agent

    def _replace_remaining_with_healing_actions(self, healer_agent: HealerAgent) -> None:
        """
        Replace all remaining replay actions and brain states with healing actions.

        Args:
            healing_actions: List of actions taken by the healing agent
            healing_brain_states: List of brain states from the healing agent
        """
        logger.info("🔄 Replacing remaining replay actions with healing actions...")

        # Convert healing brain states to BugninjaBrainState format
        healing_brain_states_converted: List[BugninjaBrainState] = []
        for brain_state_id, brain_state in healer_agent.agent_brain_states.items():
            healing_brain_states_converted.append(
                BugninjaBrainState(
                    id=brain_state_id,
                    evaluation_previous_goal=brain_state.evaluation_previous_goal,
                    memory=brain_state.memory,
                    next_goal=brain_state.next_goal,
                )
            )

        # Identify the failed brain state (the brain state of the action that failed)
        if self.replay_state_machine.passed_actions:
            failed_brain_state_id = self.replay_state_machine.current_action.brain_state_id
            healing_brain_state_id: str = healing_brain_states_converted[0].id

            for action in self.replay_state_machine.passed_actions:
                if action.brain_state_id == failed_brain_state_id:
                    action.brain_state_id = healing_brain_state_id

            self.replay_state_machine.current_action.brain_state_id = healing_brain_state_id
            rich_print("########################")
            rich_print(f"🔄 Failed brain state ID: {failed_brain_state_id}")
            rich_print(f"🔄 Replacing with healing brain state ID: {healing_brain_state_id}")
            rich_print("########################")

            # # Update all actions in passed_actions that belong to the failed brain state
            # # to reference the first healing brain state ID
            # if healing_brain_states_converted:
            #     first_healing_brain_state_id = healing_brain_states_converted[0].id
            #     for action in self.replay_state_machine.passed_actions:
            #         if action.brain_state_id == failed_brain_state_id:
            #             action.brain_state_id = first_healing_brain_state_id

        # Add all healing actions and brain states to passed collections
        self.replay_state_machine.passed_actions.extend(healer_agent.agent_taken_actions)
        self.replay_state_machine.passed_brain_states.extend(healing_brain_states_converted)

        # Clear remaining replay actions and brain states
        self.replay_state_machine.replay_actions.clear()
        self.replay_state_machine.replay_states.clear()

    async def _take_screenshot(self, action_type: str) -> str:
        """Take screenshot and return filename"""

        # Get the current extended action for highlighting
        current_action = self.replay_state_machine.current_action

        return await self.screenshot_manager.take_screenshot(
            page=self.current_page, action=current_action, browser_session=self.browser_session
        )

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory for sharing with healing agent"""
        return self.screenshot_manager.get_screenshots_dir()

    def _get_current_action_index(self) -> int:
        """Get the current action index for progress tracking."""
        return len(self.replay_state_machine.passed_actions)

    async def _get_current_url(self) -> str:
        """Get the current URL for progress tracking."""
        try:
            if hasattr(self, "browser_session") and self.browser_session:
                current_page = await self.browser_session.get_current_page()
                url = current_page.url
                if isinstance(url, str):
                    return url
        except Exception:
            pass
        return "unknown"

    # TODO! this has to be implemented properly with the new event publisher setup
    # async def _publish_run_event(self, event_type: str, data: Dict[str, Any]) -> None:
    #     """Publish event to all available publishers (NEW).

    #     Args:
    #         event_type: Type of event to publish
    #         data: Event data
    #     """
    #     if not self.event_manager or not self.run_id:
    #         return

    #     try:
    #         await self.event_manager.publish_action_event(self.run_id, event_type, data)
    #     except Exception as e:
    #         logger.warning(f"Failed to publish event {event_type}: {e}")
