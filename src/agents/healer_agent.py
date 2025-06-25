from typing import Dict, List

from browser_use.agent.service import logger  # type: ignore
from browser_use.agent.views import AgentBrain  # type: ignore
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID

from src.agents.bugninja_agent_base import BugninjaAgentBase
from src.agents.extensions import BugninjaController, extend_agent_action_with_info
from src.schemas import BugninjaExtendedAction

#! keep in mind that the HealerAgent is not inherited from BugninjaAgentBase but from the NavigatorAgent directly
#! for this reason it inherits the NavigatorAgent hooks as well


class HealerAgent(BugninjaAgentBase):

    def __init__(  # type:ignore
        self, *args, **kwargs  # type:ignore
    ) -> None:

        super().__init__(*args, **kwargs)
        self.agent_taken_actions: List[BugninjaExtendedAction] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

    async def _before_run_hook(self) -> None:
        logger.info(msg="🏁 BEFORE-Run hook called")

        #! we override the default controller with our own
        self.controller = BugninjaController()

    # ? we do not need to override the _after_run_hook for the healer agent
    async def _after_run_hook(self) -> None: ...

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

        # ? adding the taken actions to the list of agent actions
        self.agent_taken_actions.extend(extended_taken_actions)

    async def _after_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None: ...
    async def _before_action_hook(self, action: ActionModel) -> None: ...
    async def _after_action_hook(self, action: ActionModel) -> None: ...
