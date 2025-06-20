from src.agents.navigator_agent import BugninjaAgent
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.agent.views import AgentOutput  # type: ignore


class HealerAgent(BugninjaAgent):
    async def __before_action_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        action_data = await self.extract_information_from_step(
            model_output=model_output, browser_state_summary=browser_state_summary
        )
