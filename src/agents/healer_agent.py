from typing import Any, Dict, List, Optional

from browser_use.agent.service import (  # type: ignore
    logger,
)
from browser_use.agent.views import (  # type: ignore
    AgentBrain,
    AgentHistoryList,
    AgentOutput,
    DOMElementNode,
)
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from cuid2 import Cuid as CUID

from src.agents.common import AgentHookFunc
from src.agents.custom_controller import BugninjaController
from src.agents.navigator_agent import BugninjaAgent
from src.utils.selector_factory import SelectorFactory

SELECTOR_ORIENTED_ACTIONS: List[str] = [
    "click_element_by_index",
    "input_text",
    "get_dropdown_options",
    "select_dropdown_option",
    "drag_drop",
]

ALTERNATIVE_XPATH_SELECTORS_KEY: str = "alternative_relative_xpaths"
DOM_ELEMENT_DATA_KEY: str = "dom_element_data"


class HealerAgent(BugninjaAgent):
    async def __before_action_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        _ = await self.extract_information_from_step(
            model_output=model_output, browser_state_summary=browser_state_summary
        )

    @time_execution_async("--run (agent)")
    async def run(
        self,
        max_steps: int = 100,
        on_step_start: AgentHookFunc | None = None,
        on_step_end: AgentHookFunc | None = None,
    ) -> Optional[AgentHistoryList]:
        """Execute the task with maximum number of steps"""

        self.agent_taken_actions: List[Dict[str, Any]] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

        #! we override the default controller with our own
        self.controller = BugninjaController()

        results = await super().run(
            max_steps=max_steps, on_step_start=on_step_start, on_step_end=on_step_end
        )

        self.save_agent_actions()

        return results

    async def extract_information_from_step(
        self, model_output: AgentOutput = None, browser_state_summary: BrowserStateSummary = None
    ) -> List[Dict[str, Any]]:

        # TODO: documentation here

        currently_taken_actions: List[Dict[str, Any]] = []

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        for action in model_output.action:
            short_action_descriptor: Dict[str, Any] = action.model_dump(exclude_none=True)

            action_dictionary: Dict[str, Any] = {
                "brain_state_id": brain_state_id,
                "action": action.model_dump(),
                DOM_ELEMENT_DATA_KEY: None,
            }

            action_key: str = list(short_action_descriptor.keys())[-1]

            logger.info(f"📄 Action: {short_action_descriptor}")
            logger.info(f"📄 Action key: {action_key}")

            #!! these values here were selected by hand, if necessary they can be extended with other actions as well
            if action_key in SELECTOR_ORIENTED_ACTIONS:
                action_index = short_action_descriptor[action_key]["index"]
                chosen_selector: DOMElementNode = browser_state_summary.selector_map[action_index]
                logger.info(f"📄 {action_key} on {chosen_selector}")

                selector_data: Dict[str, Any] = chosen_selector.__json__()

                formatted_xpath: str = "//" + selector_data["xpath"].strip("/")

                #! adding the raw XPath to the short action descriptor (even though it is not part of the model output)
                short_action_descriptor[action_key]["xpath"] = formatted_xpath

                raw_html: str = await self.get_raw_html_of_current_page()

                try:
                    factory = SelectorFactory(raw_html)
                    selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = (
                        factory.generate_relative_xpaths_from_full_xpath(full_xpath=formatted_xpath)
                    )

                except Exception as e:
                    logger.error(f"Error generating alternative selectors: {e}")
                    selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = None

                action_dictionary[DOM_ELEMENT_DATA_KEY] = selector_data

            currently_taken_actions.append(action_dictionary)

        #! adding the taken actions to the list of agent actions
        self.agent_taken_actions.extend(currently_taken_actions)

        return currently_taken_actions
