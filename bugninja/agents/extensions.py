import asyncio
from enum import Enum
from typing import Literal, Optional

from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import ActionResult  # type: ignore
from browser_use.browser.views import BrowserError  # type: ignore
from browser_use.controller.service import Controller  # type: ignore
from browser_use.controller.views import InputTextAction  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from browser_use.dom.views import DOMElementNode  # type: ignore
from pydantic import BaseModel

from bugninja.utils.logging_config import logger


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

        @self.registry.action(
            "Input text into a input interactive element",
            param_model=InputTextAction,
        )
        async def input_text(
            params: InputTextAction,
            browser_session: BrowserSession,
            has_sensitive_data: bool = False,
        ) -> ActionResult:
            if params.index not in await browser_session.get_selector_map():
                raise Exception(
                    f"Element index {params.index} does not exist - retry or use alternative actions"
                )

            element_node: Optional[DOMElementNode] = await browser_session.get_dom_element_by_index(
                params.index
            )

            if element_node is None:
                raise Exception(f"Element index {params.index} could not be found on the page!")

            text: str = params.text

            try:
                # Highlight before typing
                # if element_node.highlight_index is not None:
                # 	await self._update_state(focus_element=element_node.highlight_index)

                element_handle = await browser_session.get_locate_element(element_node)

                if element_handle is None:
                    raise BrowserError(f"Element: {repr(element_node)} not found")

                # Ensure element is ready for input
                try:
                    await element_handle.wait_for_element_state("stable", timeout=1000)
                    is_visible = await browser_session._is_visible(element_handle)
                    if is_visible:
                        await element_handle.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass

                # Get element properties to determine input method
                tag_handle = await element_handle.get_property("tagName")
                tag_name = (await tag_handle.json_value()).lower()
                is_contenteditable = await element_handle.get_property("isContentEditable")
                readonly_handle = await element_handle.get_property("readOnly")
                disabled_handle = await element_handle.get_property("disabled")

                readonly = await readonly_handle.json_value() if readonly_handle else False
                disabled = await disabled_handle.json_value() if disabled_handle else False

                # always click the element first to make sure it's in the focus
                await element_handle.click()

                #! Bugninja edit: we not only click, but setting the value of the input text and empty string first to clear any pre-existing text
                await element_handle.press("Control+A")
                await element_handle.press("Delete")

                await asyncio.sleep(0.1)

                try:
                    if (await is_contenteditable.json_value() or tag_name == "input") and not (
                        readonly or disabled
                    ):
                        await element_handle.evaluate('el => {el.textContent = ""; el.value = "";}')
                        await element_handle.type(text, delay=5)
                    else:
                        await element_handle.fill(text)
                except Exception:
                    # last resort fallback, assume it's already focused after we clicked on it,
                    # just simulate keypresses on the entire page
                    page = await browser_session.get_current_page()
                    await page.keyboard.type(text)

            except Exception as e:
                logger.debug(
                    f"❌  Failed to input text into element: {repr(element_node)}. Error: {str(e)}"
                )
                raise BrowserError(
                    f"Failed to input text into index {element_node.highlight_index}"
                )

            if not has_sensitive_data:
                msg = f"⌨️  Input {params.text} into index {params.index}"
            else:
                msg = f"⌨️  Input sensitive data into index {params.index}"
            logger.info(msg)
            logger.debug(f"Element xpath: {element_node.xpath}")
            return ActionResult(extracted_content=msg, include_in_memory=True)
