import asyncio
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import ActionResult  # type: ignore
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
    DOMElementNode,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.service import Controller  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from pydantic import BaseModel

from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
from bugninja.schemas.pipeline import BugninjaExtendedAction
from bugninja.utils.logging_config import logger
from bugninja.utils.selector_factory import SelectorFactory

SELECTOR_ORIENTED_ACTIONS: List[str] = [
    "click_element_by_index",
    "input_text",
    "get_dropdown_options",
    "select_dropdown_option",
    "drag_drop",
]

ALTERNATIVE_XPATH_SELECTORS_KEY: str = "alternative_relative_xpaths"
DOM_ELEMENT_DATA_KEY: str = "dom_element_data"
BRAINSTATE_IDX_DATA_KEY: str = "idx_in_brainstate"


class UserInputTypeEnum(str, Enum):
    """Enumeration of user input types for authentication handling."""

    TEXT = "TEXT"
    EMPTY = "EMPTY"


class UserInputResponse(BaseModel):
    """Response model for user input during authentication flows.

    Attributes:
        user_input (Optional[str]): The user's input text, if any
        user_input_type (UserInputTypeEnum): Type of input provided
    """

    user_input: Optional[str]
    user_input_type: UserInputTypeEnum


async def get_user_input_async() -> UserInputResponse:
    """Get user input asynchronously for authentication flows.

    This function prompts the user for input and waits for their response.
    It's used during third-party authentication flows where manual intervention
    is required.

    Returns:
        UserInputResponse: The user's input response with type classification
    """
    user_input = input("▶️ Waiting for user to signal completion of the task:\n")

    if user_input == "":
        return UserInputResponse(user_input=None, user_input_type=UserInputTypeEnum.EMPTY)
    else:
        return UserInputResponse(user_input=user_input, user_input_type=UserInputTypeEnum.TEXT)


async def extend_agent_action_with_info(
    brain_state_id: str,
    current_page: Page,
    model_output: AgentOutput,
    browser_state_summary: BrowserStateSummary,
) -> List["BugninjaExtendedAction"]:
    """Extend agent actions with additional DOM element information and alternative selectors.

    This function processes agent actions and enriches them with detailed DOM element data,
    including XPath selectors and alternative relative XPath selectors for selector-oriented
    actions. It's designed to enhance action tracking and debugging capabilities by providing
    comprehensive element identification information.

    Args:
        brain_state_id (str): Unique identifier for the current brain state/agent session
        current_page (Page): Playwright page object representing the current browser page
        model_output (AgentOutput): The output from the agent model containing actions to be processed
        browser_state_summary (BrowserStateSummary): Summary of the current browser state including selector mappings

    Returns:
        List[BugninjaExtendedAction]: List of extended actions with enriched DOM element data

    Raises:
        Exception: Propagates any exceptions from SelectorFactory operations

    Notes:
        - Only selector-oriented actions (defined in SELECTOR_ORIENTED_ACTIONS) are enriched with DOM element data
        - For selector-oriented actions, the function:
          1. Extracts the element index from the action
          2. Retrieves the corresponding DOM element from browser_state_summary
          3. Formats the XPath selector
          4. Generates alternative relative XPath selectors using SelectorFactory
          5. Adds all this data to the action dictionary
        - Non-selector-oriented actions are included in the result but without DOM element data
        - The function handles exceptions during selector generation gracefully, setting alternative selectors to None if generation fails
    """
    currently_taken_actions: List["BugninjaExtendedAction"] = []

    for action_idx, action in enumerate(model_output.action):
        short_action_descriptor: Dict[str, Any] = action.model_dump(exclude_none=True)
        logger.bugninja_log(f"📄 Action: {short_action_descriptor}")

        action_dictionary: Dict[str, Any] = {
            "brain_state_id": brain_state_id,
            "action": action.model_dump(),
            "idx_in_brainstate": action_idx,
            DOM_ELEMENT_DATA_KEY: None,
        }

        action_key: str = list(short_action_descriptor.keys())[-1]
        currently_taken_actions.append(BugninjaExtendedAction.model_validate(action_dictionary))

        #!! these values here were selected by hand, if necessary they can be extended with other actions as well
        if action_key not in SELECTOR_ORIENTED_ACTIONS:
            continue

        action_index = short_action_descriptor[action_key]["index"]
        chosen_selector: DOMElementNode = browser_state_summary.selector_map[action_index]
        logger.bugninja_log(f"📄 {action_key} on {chosen_selector}")

        selector_data: Dict[str, Any] = chosen_selector.__json__()

        #! here we only want to keep the first layer of children for specific element in order to avoid unnecessarily large data dump in JSON
        ch: Dict[str, Any]

        if "children" in selector_data:
            sanitised_children: List[Dict[str, Any]] = []
            for ch in selector_data["children"]:
                ch["children"] = []
                sanitised_children.append(ch)
            selector_data["children"] = sanitised_children

        unformatted_xpath: str = selector_data["xpath"]

        # TODO! reenable for debugging
        # rich_print(f"X-Path of element: `{unformatted_xpath}`")
        # rich_print("Selector data")
        # rich_print(selector_data)

        formatted_xpath: str = "//" + unformatted_xpath.strip("/")

        #! adding the raw XPath to the short action descriptor (even though it is not part of the model output)
        short_action_descriptor[action_key]["xpath"] = formatted_xpath

        current_page_html: str = await BugninjaAgentBase.get_raw_html_of_playwright_page(
            page=current_page
        )

        selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = SelectorFactory(
            html_content=current_page_html
        ).generate_relative_xpaths_from_full_xpath(full_xpath=formatted_xpath)

        currently_taken_actions[-1].dom_element_data = selector_data

    return currently_taken_actions


class BugninjaController(Controller):
    """Extended controller with additional browser automation actions.

    This controller extends the base `Controller` class with additional actions
    specifically designed for Bugninja automation scenarios, including:
    - scrolling operations (up/down)
    - waiting mechanisms
    - third-party authentication handling

    Attributes:
        verbose (bool): Whether to enable verbose logging for controller operations

    ### Key Methods

    1. **scroll_down()** -> `ActionResult`: - Scroll down the page by specified amount
    2. **scroll_up()** -> `ActionResult`: - Scroll up the page by specified amount
    3. **wait()** -> `ActionResult`: - Wait for specified number of seconds
    4. **third_party_authentication_wait()** -> `ActionResult`: - Wait for user authentication completion
    """

    def __init__(
        self,
        exclude_actions: list[str] = [],
        output_model: type[BaseModel] | None = None,
        verbose: bool = False,
    ):
        """Initialize BugninjaController with extended functionality.

        Args:
            exclude_actions (list[str]): List of action names to exclude from the controller
            output_model (type[BaseModel] | None): Optional output model for action results
            verbose (bool): Whether to enable verbose logging
        """
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self.verbose = verbose

        async def handle_scroll(
            scroll_action: ScrollAction,
            browser_session: BrowserSession,
            type: Literal["up", "down"],
        ) -> ActionResult:
            """Handle scrolling operations with consistent behavior.

            Args:
                scroll_action (ScrollAction): The scroll action configuration
                browser_session (BrowserSession): The browser session to perform scrolling on
                type (Literal["up", "down"]): Direction of scrolling

            Returns:
                ActionResult: Result of the scrolling operation
            """
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

            logger.bugninja_log(msg)
            return ActionResult(extracted_content=msg, include_in_memory=True)

        @self.registry.action(
            "Scroll down the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_down(
            params: ScrollAction, browser_session: BrowserSession
        ) -> ActionResult:
            """Scroll down the page by specified amount.

            Args:
                params (ScrollAction): Scroll parameters including amount
                browser_session (BrowserSession): Browser session to perform scrolling on

            Returns:
                ActionResult: Result of the scrolling operation
            """
            return await handle_scroll(params, browser_session, "down")

        @self.registry.action(
            "Scroll up the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_up(params: ScrollAction, browser_session: BrowserSession) -> ActionResult:
            """Scroll up the page by specified amount.

            Args:
                params (ScrollAction): Scroll parameters including amount
                browser_session (BrowserSession): Browser session to perform scrolling on

            Returns:
                ActionResult: Result of the scrolling operation
            """
            return await handle_scroll(params, browser_session, "up")

        @self.registry.action("Wait for x seconds default 3")
        async def wait(seconds: int = 3) -> ActionResult:
            """Wait for specified number of seconds.

            Args:
                seconds (int): Number of seconds to wait (default: 3)

            Returns:
                ActionResult: Result of the waiting operation
            """
            msg = f"🕒  Waiting for {seconds} seconds"
            logger.bugninja_log(msg)
            await asyncio.sleep(seconds)
            return ActionResult(extracted_content=msg, include_in_memory=True)

        @self.registry.action(
            "Wait until a third party service/app/user finishes the authentication task for the flow to proceed",
        )
        async def third_party_authentication_wait() -> ActionResult:
            """Wait for third-party authentication completion.

            This action prompts the user to complete authentication tasks and waits
            for their signal that the authentication is complete.

            Returns:
                ActionResult: Result indicating authentication completion status
            """
            user_input: UserInputResponse = await get_user_input_async()

            if user_input.user_input_type == UserInputTypeEnum.EMPTY:
                return ActionResult(
                    extracted_content="The human signaled to the model that the third party authentication happened successfully",
                    include_in_memory=True,
                )
            else:
                return ActionResult(
                    extracted_content="The timeout means that the user is still working on the third party authentication, so the agent has to wait for a bit more",
                    include_in_memory=True,
                )
