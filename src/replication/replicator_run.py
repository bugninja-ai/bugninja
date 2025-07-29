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
from typing import List, Optional, Tuple

from browser_use.agent.views import AgentBrain  # type: ignore
from rich import print as rich_print

from src.agents.healer_agent import HealerAgent
from src.models.model_configs import azure_openai_model
from src.replication.replicator_navigation import ReplicatorError, ReplicatorNavigator
from src.schemas.pipeline import (
    BugninjaBrainState,
    BugninjaExtendedAction,
    ReplayWithHealingStateMachine,
    StateComparison,
)
from src.utils.logger_config import set_logger_config
from src.utils.screenshot_manager import ScreenshotManager

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
        json_path: str,
        fail_on_unimplemented_action: bool = False,
        sleep_after_actions: float = 1.0,
        pause_after_each_step: bool = True,
    ):
        """
        Initialize the ReplicatorRun with a JSON file path.

        Args:
            json_path: Path to the JSON file containing interaction steps
            fail_on_unimplemented_action: Whether to fail on unimplemented actions
            sleep_after_actions: Time to sleep after each action
            pause_after_each_step: Whether to pause and wait for Enter key after each step
            secrets: Dictionary of secrets to replace in actions
        """

        super().__init__(
            traversal_path=json_path,
            fail_on_unimplemented_action=fail_on_unimplemented_action,
            sleep_after_actions=sleep_after_actions,
        )

        self.traversal_path = json_path
        self.max_retries = 2
        self.retry_delay = 0.5

        self.healing_happened = False

        self.pause_after_each_step = pause_after_each_step
        self.secrets = self.replay_traversal.secrets

        # Get the number of actions from the actions dictionary
        self.total_actions = len(self.replay_traversal.actions)

        # Initialize screenshot manager
        self.screenshot_manager = ScreenshotManager(folder_prefix="replay")

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

        logger.info(f"🚀 Initialized ReplicatorRun with {self.total_actions} steps to process")
        if self.pause_after_each_step:
            logger.info(
                "⏸️ Pause after each step is ENABLED - press Enter to continue after each action"
            )
        logger.info(
            f"📸 Screenshots will be saved to: {self.screenshot_manager.get_screenshots_dir()}"
        )

    def _wait_for_enter_key(self) -> None:
        """
        Wait for the user to press the Enter key to continue.

        This method provides a pause mechanism that allows users to review
        each step before proceeding to the next one.
        """
        try:
            user_input: str = self._get_user_input()
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

    async def evaluate_current_state(
        # TODO! later add here proper typing in oder to get rid of type matching problems
        self,
        current_state: AgentBrain,
        travel_states: List[AgentBrain],
    ) -> StateComparison:
        # Read the system prompt
        system_prompt_path = Path(__file__).parent / "prompts" / "state_comp_system_prompt.md"
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()

        # Read the user prompt template
        user_prompt_path = Path(__file__).parent / "prompts" / "state_comp_user_prompt.md"
        with open(user_prompt_path, "r") as f:
            user_prompt_template = f.read()

        # Replace placeholders with actual data
        user_prompt = user_prompt_template.replace(
            "[[CURRENT_STATE_JSON]]",
            json.dumps(current_state.model_dump(), indent=4, ensure_ascii=False),
        ).replace(
            "[[TRAVEL_STATES]]",
            json.dumps(
                {
                    "travel_states": [
                        {"idx": idx} | s.model_dump() for idx, s in enumerate(travel_states)
                    ]
                },
                indent=4,
                ensure_ascii=False,
            ),
        )

        json_llm = azure_openai_model().bind(response_format={"type": "json_object"})
        ai_msg = json_llm.invoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        response_json = json.loads(ai_msg.content)  # type:ignore

        return StateComparison.model_validate(response_json)

    async def create_self_healing_agent(self) -> HealerAgent:
        """
        Start the self-healing agent.
        """
        agent = HealerAgent(
            task=self.replay_traversal.test_case,
            llm=azure_openai_model(),
            browser_session=self.browser_session,
            sensitive_data=self.secrets,
            # TODO! experiment with adding the proper state from previous runs for the brain to be aware what is happening
            # injected_agent_state=self.create_agent_state_from_traversal_json(cut_after=at_idx),
        )

        # Share screenshot directory and counter with healing agent
        agent.screenshots_dir = self.screenshot_manager.get_screenshots_dir()
        agent.screenshot_counter = self.screenshot_manager.get_screenshot_counter()
        agent.screenshot_manager = self.screenshot_manager

        await agent._before_run_hook()

        return agent

    def _save_corrected_traversal(self, output_path: str) -> None:
        """
        Save the corrected traversal containing successful actions and healer replacements.
        """
        logger.info("💾 Building corrected traversal with healer actions...")

        # overwrite the actions
        self.replay_traversal.brain_states = {
            bs.id: bs.to_agent_brain() for bs in self.replay_state_machine.passed_brain_states
        }
        self.replay_traversal.actions = {
            f"action_{i}": e for i, e in enumerate(self.replay_state_machine.passed_actions)
        }

        with open(output_path, "w") as f:
            json.dump(
                self.replay_traversal.model_dump(),
                f,
                indent=4,
                ensure_ascii=False,
            )

        logger.info(f"💾 Corrected traversal saved to: {output_path}")

    async def _run(self) -> Tuple[bool, Optional[str]]:
        failed = False
        failed_reason: Optional[str] = None

        logger.info("🚀 Starting replication with brain state-based processing")
        logger.info(
            f"📊 Total brain states to process: {len(self.replay_state_machine.replay_states)+1}"
        )

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

                logger.info(
                    "🩹 Starting free healing agent to complete entire remaining traversal..."
                )

                try:
                    # Use free healing agent to complete the entire remaining traversal
                    healing_success = await self._start_free_healing()

                    if healing_success:
                        self.healing_happened = True
                        logger.info("✅ Free healing completed entire traversal successfully")

                    else:
                        logger.error("❌ Free healing failed to complete traversal")
                        failed = True
                        failed_reason = "Free healing failed to complete traversal"
                        break

                except UserInterruptionError as e:
                    logger.info("⏹️ User interrupted the healing process")
                    failed = True
                    failed_reason = str(e)
                    break

                except Exception as healing_error:
                    logger.error("❌ === FREE HEALING FAILED ===")
                    logger.error(f"🚨 Healing error type: {type(healing_error).__name__}")
                    logger.error(f"🚨 Healing error message: {str(healing_error)}")
                    logger.error(
                        "❌ Both original action and free healing failed - stopping replication"
                    )
                    failed = True
                    failed_reason = (
                        f"Action failed: {str(e)}. Free healing failed: {str(healing_error)}"
                    )
                    break

            # Check if we need to break out of the outer loop
            if failed:
                break

        logger.info("")
        logger.info("🏁 === REPLICATION COMPLETED ===")
        logger.info(f"📊 Final status: {'❌ FAILED' if failed else '✅ SUCCESS'}")
        if failed:
            logger.info(f"🚨 Failure reason: {failed_reason}")

        # Save corrected traversal if healing happened (regardless of final status)
        if self.healing_happened:
            output_path = self.traversal_path.replace(".json", "_corrected.json")
            logger.info(f"💾 Saving corrected traversal to: {output_path}")
            self._save_corrected_traversal(output_path)
        else:
            logger.warning("⚠️ No healing occurred - no corrected traversal to save")

        return failed, failed_reason

    async def _start_free_healing(self) -> bool:
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
                return False

            if not healer_agent.agent_taken_actions:
                rich_print(healer_agent.agent_taken_actions)
                logger.error("❌ Healer agent failed to take any actions")
                return False

            if i == 0:
                # ? Set the failed action's brain state id to the healer agent's first brain state
                # ?needs in order to tie the replay together
                self.replay_state_machine.passed_actions[0].brain_state_id = list(
                    healer_agent.agent_brain_states.keys()
                )[0]

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

                    return True

            except Exception as goal_check_error:
                logger.warning(f"⚠️ Goal detection failed: {str(goal_check_error)} - continuing")

        logger.error("❌ === FREE HEALING TIMED OUT ===")
        logger.error(f"🚨 Reached maximum steps ({max_healing_steps}) without completing goal")
        return False

    def _replace_remaining_with_healing_actions(self, healer_agent: HealerAgent) -> None:
        """
        Replace all remaining replay actions and brain states with healing actions.

        Args:
            healing_actions: List of actions taken by the healing agent
            healing_brain_states: List of brain states from the healing agent
        """
        logger.info("🔄 Replacing remaining replay actions with healing actions...")

        # Convert healing brain states to BugninjaBrainState format
        healing_brain_states_converted = []
        for brain_state_id, brain_state in healer_agent.agent_brain_states.items():
            healing_brain_states_converted.append(
                BugninjaBrainState(
                    id=brain_state_id,
                    evaluation_previous_goal=brain_state.evaluation_previous_goal,
                    memory=brain_state.memory,
                    next_goal=brain_state.next_goal,
                )
            )

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
            self.current_page, current_action, self.browser_session
        )

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory for sharing with healing agent"""
        return self.screenshot_manager.get_screenshots_dir()

    def get_screenshot_counter(self) -> int:
        """Get the current screenshot counter for sharing with healing agent"""
        return self.screenshot_manager.get_screenshot_counter()
