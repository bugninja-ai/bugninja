from pathlib import Path
from typing import List, Optional

from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID
from rich import print as rich_print
from rich.markdown import Markdown

from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
from bugninja.prompts.prompt_factory import (
    BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
    HEALDER_AGENT_EXTRA_SYSTEM_PROMPT,
    get_passed_brainstates_related_prompt,
)
from bugninja.schemas.pipeline import BugninjaBrainState
from bugninja.utils.logging_config import logger
from bugninja.utils.screenshot_manager import ScreenshotManager


class HealerAgent(BugninjaAgentBase):
    """Self-healing agent for browser automation intervention and recovery.

    This agent is specifically designed for **healing interventions** when replay
    operations fail. It extends the base agent functionality with specialized
    capabilities for:
    - automatic error detection and recovery
    - screenshot capture for debugging
    - extended action tracking for healing operations
    - event publishing for healing session monitoring

    The HealerAgent inherits all hooks from `BugninjaAgentBase` and provides
    specialized implementations for healing scenarios.

    Attributes:
        agent_taken_actions (List[BugninjaExtendedAction]): All actions taken during healing
        agent_brain_states (Dict[str, AgentBrain]): Brain states throughout the healing session
        screenshot_manager (ScreenshotManager): Manager for capturing debugging screenshots

    ### Key Methods

    1. *async* **_before_run_hook()** -> `None`: - Initialize healing session and event tracking
    2. *async* **_after_run_hook()** -> `None`: - Complete healing session and event tracking
    3. *async* **_before_step_hook()** -> `None`: - Process actions and create extended actions
    4. *async* **_after_action_hook()** -> `None`: - Capture screenshots after each action
    5. *async* **run()** -> `Optional[AgentHistoryList]`: - Execute healing intervention

    Example:
        ```python
        from bugninja.agents.healer_agent import HealerAgent
        from bugninja.events import EventPublisherManager

        # Create healer agent with event tracking
        healer = HealerAgent(
            task="Fix the broken login flow",
            llm=create_llm_model_from_config(create_llm_config_from_settings()),  # Uses unified LLM configuration
            browser_session=browser_session,
            event_manager=event_manager,
            parent_run_id="original_run_id"
        )

        # Execute healing intervention
        result = await healer.run(max_steps=50)
        ```
    """

    def __init__(  # type:ignore
        self,
        *args,
        task: str,
        parent_run_id: Optional[str] = None,
        extra_instructions: List[str] = [],
        override_system_message: str = BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
        extend_system_message: str | None = None,
        already_completed_brainstates: List[BugninjaBrainState] = [],
        output_base_dir: Optional[Path] = None,
        **kwargs,  # type:ignore
    ) -> None:
        """Initialize HealerAgent with healing-specific functionality.

        Args:
            *args: Arguments passed to the parent BugninjaAgentBase class
            task (str): The healing task description for the agent to execute
            parent_run_id (Optional[str]): ID of the parent run for event tracking continuity
            extra_instructions (List[str]): Additional instructions to append to the task
            override_system_message (str): System message to override the default (defaults to navigator prompt)
            extend_system_message (str | None): Additional system message to extend the default
            already_completed_brainstates (List[BugninjaBrainState]): Previously completed brain states for context
            output_base_dir (Optional[Path]): Base directory for all output files (traversals, screenshots, videos)
            **kwargs: Keyword arguments passed to the parent BugninjaAgentBase class
        """

        task += f"\n\n{get_passed_brainstates_related_prompt(completed_brain_states=already_completed_brainstates)}"

        system_message_to_extend_by: str = extend_system_message if extend_system_message else ""

        super().__init__(
            *args,
            override_system_message=override_system_message,
            extend_system_message=system_message_to_extend_by
            + f"\n\n{HEALDER_AGENT_EXTRA_SYSTEM_PROMPT}",
            extra_instructions=extra_instructions,
            task=task,
            **kwargs,
        )

        # Store output base directory
        self.output_base_dir = output_base_dir

        # Use parent's run_id if provided, otherwise keep the generated one
        if parent_run_id is not None:
            self.run_id = parent_run_id

        rich_print("--> Formatted task provided to the agent:")
        rich_print(Markdown(self.task))

    async def _before_run_hook(self) -> None:
        """Initialize healing session with event tracking and screenshot management.

        This hook sets up the healing environment by:
        - initializing screenshot manager for debugging
        - setting up event tracking for healing operations
        - logging the start of the healing intervention
        """
        logger.bugninja_log("🏁 BEFORE-Run hook called")

        # Initialize screenshot manager (will be overridden if shared from replay)
        if not hasattr(self, "screenshot_manager"):
            self.screenshot_manager = ScreenshotManager(
                run_id=self.run_id, base_dir=self.output_base_dir
            )

        # Initialize event tracking for healing run (if event_manager is provided)
        if self.event_manager and self.event_manager.has_publishers():
            try:
                await self.event_manager.initialize_run(
                    run_type="healing",
                    metadata={
                        "task_description": "Healing intervention",
                        "original_task": getattr(self, "task", "Unknown"),
                    },
                    existing_run_id=self.run_id,  # Use existing run_id instead of generating new one
                )
                logger.bugninja_log(f"🎯 Started healing run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

    # ? we do not need to override the _after_run_hook for the healer agent
    async def _after_run_hook(self) -> None:
        """Complete event tracking for healing run.

        This hook finalizes the event tracking for healing interventions,
        marking the run as completed or failed based on the final result.

        The hook:
        - checks for successful completion of healing operations
        - publishes final run status to event managers
        - logs completion status for monitoring
        """
        # Complete event tracking for healing run
        if self.event_manager and self.run_id:
            try:
                if not self.state.last_result:
                    raise Exception("No results found for healing run")

                success = not any(
                    result.error for result in self.state.last_result if hasattr(result, "error")
                )
                await self.event_manager.complete_run(self.run_id, success)
                logger.bugninja_log(f"✅ Completed healing run: {self.run_id}")

            except Exception as e:
                logger.warning(f"Failed to complete event tracking: {e}")

    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """Process actions and create extended actions for healing operations.

        This hook is called before each step in the healing process and:
        - creates brain state tracking for the current step
        - generates extended actions with DOM element information
        - associates actions with their extended versions
        - stores actions for later analysis and debugging

        Args:
            browser_state_summary (BrowserStateSummary): Current browser state information
            model_output (AgentOutput): Model output containing actions to be executed
        """
        logger.bugninja_log("🪝 BEFORE-Step hook called")

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        current_page: Page = await self.browser_session.get_current_page()

        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        extended_taken_actions = await self.extend_model_output_with_info(
            brain_state_id=brain_state_id,
            current_page=current_page,
            model_output=model_output,
            browser_state_summary=browser_state_summary,
        )

        # Store extended actions for hook access
        self.current_step_extended_actions = extended_taken_actions

        # Associate each action with its corresponding extended action index
        for i, action in enumerate(model_output.action):
            self._associate_action_with_extended_action(action, i)

    async def _after_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None:
        """Clean up action mapping after step completion.

        This hook clears the action mapping to prevent memory accumulation
        and ensure clean state for the next step.

        Args:
            browser_state_summary (BrowserStateSummary): Browser state after step completion
            model_output (AgentOutput): Model output from the completed step
        """
        # Clear action mapping to prevent memory accumulation
        self._clear_action_mapping()

    async def _before_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Hook called before each action (no-op implementation).

        Args:
            action (ActionModel): The action about to be executed
        """
        logger.info(
            msg=f"🪝 BEFORE-Action hook called for action #{len(self.agent_taken_actions)+1} in traversal"
        )

    async def _after_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Capture screenshot after action execution for debugging.

        This hook takes a screenshot after each action is completed,
        highlighting the element that was interacted with for debugging
        and analysis purposes.

        Args:
            action (ActionModel): The action that was just executed
        """

        logger.info(
            msg=f"🪝 AFTER-Action hook called for action #{len(self.agent_taken_actions)+1}"
        )

        # ? adding the taken action to the list of agent actions
        self.agent_taken_actions.append(self.current_step_extended_actions[action_idx_in_step])
