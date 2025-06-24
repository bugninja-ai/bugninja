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
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import print as rich_print

from src.agents.healer_agent import HealerAgent
from src.models.model_configs import azure_openai_model
from src.replicator_navigation import ReplicatorError, ReplicatorNavigator
from src.schemas import (
    BrainStateProgressTracker,
    BugninjaExtendedAction,
    StateComparison,
)

# Configure logging with custom format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
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

        # Initialize brain state progress tracker
        self.progress_tracker = BrainStateProgressTracker()
        self.progress_tracker.initialize_from_traversal(self.replay_traversal.actions)

        logger.info(f"🚀 Initialized ReplicatorRun with {self.total_actions} steps to process")
        logger.info(f"📊 Initialized {len(self.progress_tracker.brain_states)} brain states")
        if self.pause_after_each_step:
            logger.info(
                "⏸️ Pause after each step is ENABLED - press Enter to continue after each action"
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
        current_state: Dict[str, Any],
        upcoming_states: List[Dict[str, Any]],
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
            "[[CURRENT_STATE_JSON]]", json.dumps(current_state, indent=4, ensure_ascii=False)
        ).replace(
            "[[UPCOMING_STATES]]",
            json.dumps(
                {"upcoming_states": [{"idx": idx} | s for idx, s in enumerate(upcoming_states)]},
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
        rich_print(type(response_json))
        rich_print(response_json)

        return StateComparison.model_validate(response_json)

    async def create_self_healing_agent(self, at_idx: int) -> HealerAgent:
        """
        Start the self-healing agent.
        """
        current_brain_state = self.progress_tracker.get_current_brain_state()
        target_brain_state_id = current_brain_state.brain_state_id if current_brain_state else None

        agent = HealerAgent(
            task=self.replay_traversal.test_case,
            llm=azure_openai_model(),
            browser_session=self.browser_session,
            sensitive_data=self.secrets,
            target_brain_state_id=target_brain_state_id,
            # TODO! experiment with adding the proper state from previous runs for the brain to be aware what is happening
            # injected_agent_state=self.create_agent_state_from_traversal_json(cut_after=at_idx),
        )

        await agent._before_run_hook()

        return agent

    def _save_corrected_traversal(self, output_path: str) -> None:
        """
        Save the corrected traversal containing successful actions and healer replacements.
        """
        logger.info("💾 Building corrected traversal with healer actions...")

        # Use the progress tracker to build corrected actions
        corrected_actions = self.progress_tracker.build_corrected_actions()

        # overwrite the actions
        self.replay_traversal.actions = corrected_actions

        with open(output_path, "w") as f:
            json.dump(
                self.replay_traversal.model_dump(),
                f,
                indent=4,
                ensure_ascii=False,
            )

        logger.info(f"💾 Corrected traversal saved to: {output_path}")
        logger.info(f"📊 Total actions in corrected traversal: {len(corrected_actions)}")

    def _validate_state_consistency(self) -> bool:
        """
        Validate that the current state is consistent after healing.

        Returns:
            True if state is consistent, False otherwise
        """
        current_brain_state = self.progress_tracker.get_current_brain_state()
        if not current_brain_state:
            logger.warning("⚠️ No current brain state to validate")
            return False

        # Check if brain state is exactly complete
        if not current_brain_state.is_exactly_complete():
            logger.warning(
                f"⚠️ Brain state '{current_brain_state.brain_state_id}' is not exactly complete after healing"
            )
            logger.warning(f"   - Expected: {len(current_brain_state.original_actions)} actions")
            logger.warning(
                f"   - Actual: {len(current_brain_state.completed_actions)} completed + {len(current_brain_state.healer_actions)} healer"
            )
            return False

        # Check if status is properly set
        if current_brain_state.status != "completed":
            logger.warning(
                f"⚠️ Brain state '{current_brain_state.brain_state_id}' status is '{current_brain_state.status}', expected 'completed'"
            )
            return False

        logger.info(
            f"✅ State consistency validated for brain state '{current_brain_state.brain_state_id}'"
        )
        return True

    async def _run(self) -> Tuple[bool, Optional[str]]:
        failed = False
        failed_reason: Optional[str] = None

        # Track successful actions for corrected traversal
        successful_actions = {}

        logger.info("🚀 Starting replication with brain state-based processing")
        logger.info(f"📊 Total brain states to process: {len(self.progress_tracker.brain_states)}")

        # Process brain states sequentially
        while True:
            # Get the next brain state to process
            next_brain_state_id = self.progress_tracker.get_next_brain_state()

            if not next_brain_state_id:
                logger.info("✅ All brain states completed successfully")
                break

            # Set current brain state
            self.progress_tracker.set_current_brain_state(next_brain_state_id)

            logger.info("")
            logger.info(f"🧠 === PROCESSING BRAIN STATE '{next_brain_state_id}' ===")

            # Get actions for this brain state
            brain_state_actions = self.progress_tracker.get_current_actions()
            total_actions_in_state = len(brain_state_actions)

            logger.info(f"📊 Brain state has {total_actions_in_state} actions to process")

            # Process actions within this brain state
            action_idx = 0
            while action_idx < total_actions_in_state:
                brain_state_action = brain_state_actions[action_idx]
                action_key = brain_state_action.action_key
                action = brain_state_action.action

                logger.info("")
                logger.info(f"🔄 === PROCESSING ACTION {action_key} ===")
                logger.info(f"📍 Action index: {action_idx}/{total_actions_in_state}")
                logger.info(f"🧠 Brain state: {next_brain_state_id}")
                logger.info(
                    f"📋 Action type: {list(action.action.keys())[0] if action.action else 'Unknown'}"
                )

                # Log action details
                if action.action:
                    action_type = list(action.action.keys())[0]
                    if action_type == "click":
                        element_info = action.dom_element_data
                        if element_info:
                            logger.info(
                                f"🎯 Clicking element: {element_info.get('tag_name', 'Unknown')} with text: '{element_info.get('text', 'N/A')[:50]}...'"
                            )
                    elif action_type == "input_text":
                        text = action.action.get("input_text", {}).get("text", "")
                        logger.info(
                            f"⌨️ Inputting text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
                        )
                    elif action_type == "go_to_url":
                        url = action.action.get("go_to_url", {}).get("url", "")
                        logger.info(f"🌐 Navigating to URL: {url}")
                    else:
                        logger.info(f"⚙️ Performing action: {action_type}")

                try:
                    logger.info("▶️ Executing action...")
                    await self._execute_action(action)
                    logger.info("✅ Action executed successfully")

                    # Mark action as completed
                    self.progress_tracker.mark_action_completed(action_key)

                    # Track successful action for corrected traversal
                    successful_actions[action_key] = action

                    # Add pause after action if enabled
                    if self.pause_after_each_step:
                        self._wait_for_enter_key()

                    # Move to next action
                    action_idx += 1

                except UserInterruptionError as e:
                    logger.info("⏹️ User interrupted replication process")
                    failed = True
                    failed_reason = str(e)
                    break

                except Exception as e:
                    logger.error("")
                    logger.error(f"❌ === ACTION {action_key} FAILED ===")
                    logger.error(f"🚨 Error type: {type(e).__name__}")
                    logger.error(f"🚨 Error message: {str(e)}")
                    logger.error(f"📍 Failed at action index: {action_idx}")
                    logger.error(f"🧠 Failed in brain state: {next_brain_state_id}")

                    # Mark action as failed
                    self.progress_tracker.mark_action_failed(action_idx)

                    logger.info("🩹 Starting healer agent to complete this brain state...")

                    try:
                        # Use healer agent to complete the current brain state
                        healing_success = await self._heal_current_brain_state(action_idx)

                        if healing_success:
                            self.healing_happened = True
                            logger.info(
                                f"✅ Brain state '{next_brain_state_id}' completed successfully with healer assistance"
                            )

                            # Validate state consistency after healing
                            if not self._validate_state_consistency():
                                logger.warning(
                                    "⚠️ State inconsistency detected after healing - continuing anyway"
                                )

                            # Add pause after healing if enabled
                            if self.pause_after_each_step:
                                self._wait_for_enter_key()

                            # Move to next brain state
                            break
                        else:
                            logger.error(
                                f"❌ Healer failed to complete brain state '{next_brain_state_id}'"
                            )
                            failed = True
                            failed_reason = (
                                f"Healer failed to complete brain state {next_brain_state_id}"
                            )
                            break

                    except UserInterruptionError as e:
                        logger.info("⏹️ User interrupted the healing process")
                        failed = True
                        failed_reason = str(e)
                        break

                    except Exception as healing_error:
                        logger.error("❌ === HEALING FAILED ===")
                        logger.error(f"🚨 Healing error type: {type(healing_error).__name__}")
                        logger.error(f"🚨 Healing error message: {str(healing_error)}")
                        logger.error(
                            "❌ Both original action and healing failed - stopping replication"
                        )
                        failed = True
                        failed_reason = (
                            f"Action failed: {str(e)}. Healing failed: {str(healing_error)}"
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

        # Log brain state completion statistics
        stats = self.progress_tracker.get_completion_stats()
        logger.info(
            f"🧠 Brain states completed: {stats['completed_states']}/{stats['total_states']}"
        )
        logger.info(
            f"📝 Actions completed: {stats['total_completed_actions']}/{stats['total_original_actions']} (original) + {stats['total_healer_actions']} (healer)"
        )

        # Save corrected traversal if we have successful actions
        if not failed and self.healing_happened:
            output_path = self.traversal_path.replace(".json", "_corrected.json")
            logger.info(f"💾 Saving corrected traversal to: {output_path}")
            self._save_corrected_traversal(output_path)
        else:
            logger.warning("⚠️ No successful actions to save in corrected traversal")

        return failed, failed_reason

    async def _heal_current_brain_state(self, failed_action_idx: int) -> bool:
        """
        Use healer agent to replace failed actions and complete the current brain state.

        Args:
            failed_action_idx: The index of the failed action within the current brain state

        Returns:
            True if brain state was completed successfully, False otherwise
        """
        current_brain_state = self.progress_tracker.get_current_brain_state()
        if not current_brain_state:
            logger.error("❌ No current brain state to heal")
            return False

        logger.info("")
        logger.info(f"🩹 === HEALING BRAIN STATE '{current_brain_state.brain_state_id}' ===")
        logger.info(f"📍 Failed action index: {failed_action_idx}")
        logger.info(
            f"📊 Original actions in brain state: {len(current_brain_state.original_actions)}"
        )
        logger.info(f"📊 Completed actions: {len(current_brain_state.completed_actions)}")
        logger.info(f"📊 Healer actions: {len(current_brain_state.healer_actions)}")

        remaining_actions = current_brain_state.get_remaining_actions()
        logger.info(f"📊 Remaining actions to complete: {remaining_actions}")

        # Create healer agent
        healer_agent = await self.create_self_healing_agent(at_idx=failed_action_idx)

        # Check completion BEFORE taking step to prevent overstepping
        if current_brain_state.is_exactly_complete():
            logger.info("✅ Brain state exactly complete - stopping healer immediately")
            current_brain_state.status = "completed"
            return True

        logger.info("")
        logger.info("🩹 === HEALER STEP ===")

        # Execute healer step
        try:
            await healer_agent.step()
        except Exception as e:
            if "Target brain state completed - stopping healer" in str(e):
                logger.info("✅ Healer agent stopped because target brain state was completed")
                # Check if brain state is actually complete
                if current_brain_state.is_exactly_complete():
                    logger.info("✅ Brain state exactly complete - stopping healer immediately")
                    current_brain_state.status = "completed"
                    return True
                else:
                    logger.warning("⚠️ Healer stopped but brain state is not complete - continuing")
            else:
                # Re-raise other exceptions
                raise e

        if not healer_agent.agent_taken_actions:
            logger.error("❌ Healer agent failed to take any actions")
            return False

        # Get the latest healer action

        for taken_healer_action in healer_agent.agent_taken_actions:
            brain_state_id = taken_healer_action.brain_state_id
            if not brain_state_id:
                logger.error("❌ Healer action missing brain_state_id")
                return False

            # Convert healer action to BugninjaExtendedAction format
            healer_extended_action = BugninjaExtendedAction(
                brain_state_id=current_brain_state.brain_state_id,
                action=taken_healer_action.action,
                dom_element_data=taken_healer_action.dom_element_data,
            )

            # Add healer action to current brain state
            self.progress_tracker.add_healer_action(healer_extended_action)

        # Log progress after adding healer action
        logger.info(
            f"📊 Progress: {len(current_brain_state.completed_actions)} completed + {len(current_brain_state.healer_actions)} healer = {len(current_brain_state.completed_actions) + len(current_brain_state.healer_actions)}/{len(current_brain_state.original_actions)} total"
        )

        # Check if we've completed enough actions to finish this brain state
        if current_brain_state.is_exactly_complete():
            logger.info("")
            logger.info(
                f"✅ === BRAIN STATE '{current_brain_state.brain_state_id}' EXACTLY COMPLETED ==="
            )
            logger.info("📊 Final stats:")
            logger.info(f"   - Original actions: {len(current_brain_state.original_actions)}")
            logger.info(f"   - Completed actions: {len(current_brain_state.completed_actions)}")
            logger.info(f"   - Healer actions: {len(current_brain_state.healer_actions)}")
            logger.info(f"   - Failed action index: {current_brain_state.failed_action_index}")

            # Mark brain state as completed and return immediately
            current_brain_state.status = "completed"
            logger.info("🛑 Brain state exactly completed - stopping healer immediately")
            return True

        # Add pause if enabled
        if self.pause_after_each_step:
            self._wait_for_enter_key()

        return False
