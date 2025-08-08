from typing import Dict, List, Optional

from browser_use.agent.service import logger  # type: ignore
from browser_use.agent.views import AgentBrain  # type: ignore
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID

from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
from bugninja.agents.extensions import BugninjaController, extend_agent_action_with_info
from bugninja.schemas.pipeline import BugninjaExtendedAction
from bugninja.utils.screenshot_manager import ScreenshotManager

#! keep in mind that the HealerAgent is not inherited from BugninjaAgentBase but from the NavigatorAgent directly
#! for this reason it inherits the NavigatorAgent hooks as well


class HealerAgent(BugninjaAgentBase):

    def __init__(  # type:ignore
        self, *args, parent_run_id: Optional[str] = None, **kwargs  # type:ignore
    ) -> None:

        super().__init__(*args, **kwargs)

        # Use parent's run_id if provided, otherwise keep the generated one
        if parent_run_id is not None:
            self.run_id = parent_run_id

        self.agent_taken_actions: List[BugninjaExtendedAction] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

    async def _before_run_hook(self) -> None:
        logger.info(msg="🏁 BEFORE-Run hook called")

        #! we override the default controller with our own
        self.controller = BugninjaController()

        # Initialize screenshot manager (will be overridden if shared from replay)
        if not hasattr(self, "screenshot_manager"):
            self.screenshot_manager = ScreenshotManager(folder_prefix="healing")

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
                logger.info(f"🎯 Started healing run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

    # ? we do not need to override the _after_run_hook for the healer agent
    async def _after_run_hook(self) -> None:
        """Complete event tracking for healing run.

        This hook finalizes the event tracking for healing interventions,
        marking the run as completed or failed based on the final result.
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
                logger.info(f"✅ Completed healing run: {self.run_id}")

            except Exception as e:
                logger.warning(f"Failed to complete event tracking: {e}")

    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:

        logger.info(msg="🪝 BEFORE-Step hook called")

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        current_page: Page = await self.browser_session.get_current_page()

        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        extended_taken_actions = await extend_agent_action_with_info(
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

        # ? adding the taken actions to the list of agent actions
        self.agent_taken_actions.extend(extended_taken_actions)

    async def _after_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None:
        # Clear action mapping to prevent memory accumulation
        self._clear_action_mapping()

    async def _before_action_hook(self, action: ActionModel) -> None: ...

    async def _after_action_hook(self, action: ActionModel) -> None:
        """Take screenshot after action execution"""
        await self.browser_session.remove_highlights()

        current_page = await self.browser_session.get_current_page()

        # Get the extended action for screenshot with highlighting
        extended_action = self._find_matching_extended_action(action)

        if not extended_action:
            raise Exception("Extended action not found for screenshot")

        screenshot_filename = await self.screenshot_manager.take_screenshot(
            current_page, extended_action, self.browser_session
        )

        # Store screenshot filename with extended action
        extended_action.screenshot_filename = screenshot_filename
        logger.info(f"📸 Stored screenshot filename: {screenshot_filename}")
