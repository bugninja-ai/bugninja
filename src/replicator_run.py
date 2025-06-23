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
from src.replicator_navigation import ActionError, ReplicatorError, ReplicatorNavigator
from src.schemas import StateComparison

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

        self.max_retries = 2
        self.retry_delay = 0.5

        self.pause_after_each_step = pause_after_each_step
        self.secrets = self.replay_traversal.secrets

        # Get the number of actions from the actions dictionary
        self.total_actions = len(self.replay_traversal.actions)
        logger.info(f"🚀 Initialized ReplicatorRun with {self.total_actions} steps to process")
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

        response_json: Dict[str, Any] = ai_msg.content  # type: ignore

        return StateComparison.model_validate(response_json)

    # def create_agent_state_from_traversal_json(self, cut_after: Optional[int] = None) -> AgentState:
    #     """
    #     Convert brain states from the loaded traversal JSON to AgentState structure.

    #     This method takes the brain_states from the replay JSON and converts them
    #     into the proper AgentState structure that can be used by the healer agent.

    #     Returns:
    #         AgentState: Complete agent state with history from the traversal JSON
    #     """
    #     agent_history_list = []

    #     # Process each brain state in chronological order
    #     for action_key in sorted(self.replay_traversal["actions"].keys()):
    #         action_data = self.replay_traversal["actions"][action_key]
    #         brain_state_id = action_data["model_taken_action"].get("brain_state_id")

    #         if brain_state_id and brain_state_id in self.brain_states:
    #             brain_state = self.brain_states[brain_state_id]

    #             # Create AgentBrain from the brain state
    #             agent_brain = AgentBrain(
    #                 evaluation_previous_goal=brain_state.get("evaluation_previous_goal", ""),
    #                 memory=brain_state.get("memory", ""),
    #                 next_goal=brain_state.get("next_goal", ""),
    #             )

    #             # Create AgentOutput with the brain state and empty action
    #             agent_output = AgentOutput(
    #                 current_state=agent_brain,
    #                 action=[],  # Empty action list since this is historical data
    #             )

    #             # Create minimal BrowserStateHistory
    #             # Note: We don't have detailed browser state info in the JSON
    #             browser_state = BrowserStateHistory(
    #                 url="",  # Could be extracted from action if needed
    #                 title="",
    #                 interacted_element=[],
    #                 tabs=[],
    #             )

    #             # Create AgentHistory entry
    #             agent_history = AgentHistory(
    #                 model_output=agent_output,
    #                 result=[],  # Empty result since this is historical data
    #                 state=browser_state,
    #             )

    #             agent_history_list.append(agent_history)

    #     # Create AgentHistoryList
    #     history_list = AgentHistoryList(history=agent_history_list)

    #     if cut_after:
    #         history_list.history = history_list.history[:cut_after]

    #     # Create and return AgentState
    #     return AgentState(history=history_list)

    def create_self_healing_agent(self, at_idx: int) -> HealerAgent:
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

        return agent

    async def self_healing_action(self, at_idx: int) -> None:

        #!!!! TODO! First try goes with BARE self healing agent
        #!!!! - No previous thought process provided
        #!!!! - No previous history provided yet

        upcoming_state_ids: List[str] = [
            brain_state_id
            for brain_state_id in self.brain_states.keys()
            if brain_state_id not in self.brain_states_passed
        ]

        upcoming_states: List[Dict[str, Any]] = [
            self.brain_states.get(brain_state_id) for brain_state_id in upcoming_state_ids
        ]

        healer_agent: HealerAgent = self.create_self_healing_agent(at_idx=at_idx)

        # TODO! healing agent should have its own complex implementation of running
        await healer_agent.step()

        if not len(healer_agent.agent_taken_actions):
            raise ActionError(
                "Self healing agent failed to find a solution for this specific state"
            )

        brain_state_id: Optional[str] = healer_agent.agent_taken_actions[-1].get("brain_state_id")

        if not brain_state_id:
            raise ActionError(
                "There is an error relating to pairing 'brain_state_id' to specific actions!"
            )

        healer_agent_state: Dict[str, Any] = healer_agent.agent_brain_states[brain_state_id]

        rich_print(
            [self.brain_states.get(brain_state_id) for brain_state_id in self.brain_states_passed]
        )
        rich_print(healer_agent_state)
        rich_print(upcoming_states)

        model_response: StateComparison = await self.evaluate_current_state(
            current_state=healer_agent_state, upcoming_states=upcoming_states
        )

        rich_print(model_response)

    async def _run(self) -> Tuple[bool, Optional[str]]:

        failed = False
        failed_reason: Optional[str] = None

        # Process actions in order
        for idx, (element_key, interaction) in enumerate(self.replay_traversal.actions.items()):
            action_key = f"action_{idx}"
            if element_key != action_key:
                error_msg: str = (
                    f"⚠️ There is a mismatch between element key and action key! '{element_key}' != '{action_key}'"
                )
                logger.error(error_msg)
                raise ActionError(error_msg)

            logger.info(f"📝 Executing interaction: {action_key}")

            try:
                # TODO! needs much more robust error handling for different kinds of errors
                await self._execute_action(interaction)

                brain_state_id = interaction.brain_state_id

                # ? mark current state as passed
                if brain_state_id not in self.brain_states_passed:
                    self.brain_states_passed.append(brain_state_id)

                # Add pause after action if enabled and action was not skipped
                if self.pause_after_each_step:
                    self._wait_for_enter_key()

            except UserInterruptionError as e:
                logger.info("⏹️ User interrupted replication process")
                failed = True
                failed_reason = str(e)
                break

            except Exception as e:
                logger.error(f"❌ Error in interaction {action_key}: {str(e)}")
                logger.info("🔄 Attempting self-healing...")
                logger.info("Marking current state as failed...")

                # ? this functionality here is crucial for handling the "failing states"
                # ? since a single state can have multiple action, an action can fail in the middle of a state
                # ? to prevent from excluding the state from comparison we need to keep track of the last passed state
                # ? here we flag the last state as not passed
                self.brain_states_passed.pop(-1)

                try:
                    # Attempt self-healing

                    await self.self_healing_action(at_idx=idx)

                    # Add pause after healing if enabled
                    if self.pause_after_each_step:
                        self._wait_for_enter_key()

                except UserInterruptionError as e:
                    logger.info("⏹️ User interrupted the healing process")
                    failed = True
                    failed_reason = str(e)
                    break

                except Exception as healing_error:
                    logger.error(f"❌ Self-healing failed: {str(healing_error)}")
                    logger.error(
                        "❌ Both original action and self-healing failed - stopping replication"
                    )
                    failed = True
                    failed_reason = (
                        f"Action failed: {str(e)}. Self-healing failed: {str(healing_error)}"
                    )

                    break

        return failed, failed_reason
