from typing import Any, Dict, List, Literal

from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import ActionResult  # type: ignore
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
    DOMElementNode,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.service import Controller, logger  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from pydantic import BaseModel

from src.agents.bugninja_agent_base import BugninjaAgentBase
from src.schemas import BugninjaExtendedAction
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


async def extend_agent_action_with_info(
    brain_state_id: str,
    current_page: Page,
    model_output: AgentOutput = None,
    browser_state_summary: BrowserStateSummary = None,
) -> List[BugninjaExtendedAction]:
    """
    Extends agent actions with additional DOM element information and alternative selectors.

    This function processes agent actions and enriches them with detailed DOM element data,
    including XPath selectors and alternative relative XPath selectors for selector-oriented
    actions. It's designed to enhance action tracking and debugging capabilities by providing
    comprehensive element identification information.

    Args:
        **brain_state_id** (str): Unique identifier for the current brain state/agent session.
        **current_page** (Page): Playwright page object representing the current browser page.
        **model_output** (AgentOutput, optional): The output from the agent model containing
            actions to be processed. Defaults to None.
        **browser_state_summary** (BrowserStateSummary, optional): Summary of the current
            browser state including selector mappings. Defaults to None.

    Returns:
        **List[BugninjaExtendedAction]**: List of extended actions with enriched DOM element data.
            Each action contains:
            - brain_state_id: The session identifier
            - action: The original action data
            - dom_element_data: Enhanced DOM element information (if applicable)

    Raises:
        Exception: Propagates any exceptions from SelectorFactory operations.

    Notes:
        - Only selector-oriented actions (defined in SELECTOR_ORIENTED_ACTIONS) are enriched
          with DOM element data
        - For selector-oriented actions, the function:
          1. Extracts the element index from the action
          2. Retrieves the corresponding DOM element from browser_state_summary
          3. Formats the XPath selector
          4. Generates alternative relative XPath selectors using SelectorFactory
          5. Adds all this data to the action dictionary
        - Non-selector-oriented actions are included in the result but without DOM element data
        - The function handles exceptions during selector generation gracefully, setting
          alternative selectors to None if generation fails
    """

    currently_taken_actions: List[BugninjaExtendedAction] = []

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

            current_page_html: str = await BugninjaAgentBase.get_raw_html_of_playwright_page(
                page=current_page
            )

            try:
                factory = SelectorFactory(current_page_html)
                selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = (
                    factory.generate_relative_xpaths_from_full_xpath(full_xpath=formatted_xpath)
                )

            except Exception as e:
                logger.error(f"Error generating alternative selectors: {e}")
                selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = None

            action_dictionary[DOM_ELEMENT_DATA_KEY] = selector_data

        currently_taken_actions.append(BugninjaExtendedAction.model_validate(action_dictionary))

    return currently_taken_actions


class BugninjaController(Controller):

    def __init__(
        self,
        exclude_actions: list[str] = [],
        output_model: type[BaseModel] | None = None,
        verbose: bool = False,
    ):
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self.verbose = verbose

        async def handle_scroll(
            scroll_action: ScrollAction,
            browser_session: BrowserSession,
            type: Literal["up", "down"],
        ) -> ActionResult:
            page = await browser_session.get_current_page()
            page_height = await page.evaluate("() => window.innerHeight")
            dy = scroll_action.amount or page_height

            if type == "up":
                dy = -dy

            await page.wait_for_load_state("load")

            # ? version#1
            # container_scrolling_success = await self._scroll_container(page, dy)

            # ? version#2
            # await page.evaluate("(y) => window.scrollBy(0, y)", dy)

            # ? version#3
            await page.mouse.wheel(delta_x=0, delta_y=dy)

            msg = f"🔍 Scrolled down the page by {dy} pixels"

            logger.info(msg)
            return ActionResult(extracted_content=msg, include_in_memory=True)

        @self.registry.action(
            "Scroll down the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_down(
            params: ScrollAction, browser_session: BrowserSession
        ) -> ActionResult:
            return await handle_scroll(params, browser_session, "down")

        @self.registry.action(
            "Scroll up the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_up(params: ScrollAction, browser_session: BrowserSession) -> ActionResult:
            return await handle_scroll(params, browser_session, "up")
