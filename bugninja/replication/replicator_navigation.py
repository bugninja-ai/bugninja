import asyncio
import gc
import json
import sys
from abc import ABC
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from browser_use import BrowserProfile, BrowserSession  # type: ignore
from browser_use.agent.views import AgentBrain  # type: ignore
from cuid2 import Cuid as CUID
from patchright.async_api import BrowserContext as PatchrightBrowserContext
from patchright.async_api import Page

from bugninja.replication.errors import ActionError, ReplicatorError, SelectorError
from bugninja.schemas.pipeline import BugninjaExtendedAction, Traversal
from bugninja.utils.logging_config import logger


def get_user_input() -> str:
    """
    Robust input method that forces stdin to work.
    """
    logger.bugninja_log("⏸️ Press Enter to continue, or enter 'q' to quit...")

    # Try to reopen stdin if it's not working
    try:
        if not sys.stdin.isatty():
            # Force reopen stdin
            sys.stdin = open("/dev/tty", "r")
    except Exception:
        logger.warning("⚠️ Failed to reopen stdin - continuing automatically")

    try:
        return input()
    except EOFError:
        # Try alternative approach
        try:
            import select
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        ch = sys.stdin.read(1)
                        if ch == "\n" or ch == "\r":
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ""
        except Exception:
            logger.warning("⚠️ No input available - continuing automatically")
            return ""
    except Exception as e:
        logger.warning(f"⚠️ Input error: {e} - continuing automatically")
        return ""


class ReplicatorNavigator(ABC):
    secrets: Dict[str, str]

    @staticmethod
    def _load_traversal_from_json(json_path: str) -> Traversal:
        """
        Load and parse the JSON file containing interaction steps.

        Returns:
            Dict containing the parsed JSON data
        """
        try:
            with open(json_path, "r") as f:
                data: Dict[str, Any] = json.load(f)  # type:ignore
                if "actions" not in data:
                    raise ReplicatorError("JSON file must contain an 'actions' key")
                return Traversal.model_validate(data)
        except Exception as e:
            raise ReplicatorError(f"Failed to load JSON file: {str(e)}")

    @staticmethod
    def _load_traversal_from_source(traversal_source: Union[str, Traversal]) -> Traversal:
        """
        Load traversal from either a JSON file path or a Traversal object.

        Args:
            traversal_source: Either a JSON file path (str) or a Traversal object

        Returns:
            Traversal: The loaded or provided traversal object

        Raises:
            ReplicatorError: If loading fails or source is invalid
        """
        if isinstance(traversal_source, str):
            # Load from JSON file
            return ReplicatorNavigator._load_traversal_from_json(traversal_source)
        elif isinstance(traversal_source, Traversal):
            # Use provided Traversal object directly
            return traversal_source
        else:
            raise ReplicatorError(
                f"Invalid traversal source type: {type(traversal_source)}. "
                "Expected str (file path) or Traversal object."
            )

    def __init__(
        self,
        traversal_source: Union[str, Traversal],
        fail_on_unimplemented_action: bool = True,
        sleep_after_actions: float = 1.0,
    ):
        self.replay_traversal = self._load_traversal_from_source(traversal_source)
        self.brain_states: Dict[str, AgentBrain] = self.replay_traversal.brain_states
        self.fail_on_unimplemented_action = fail_on_unimplemented_action
        self.sleep_after_actions = sleep_after_actions
        self.brain_states_passed: List[str] = []

        # Generate run_id for browser isolation
        self.run_id = CUID().generate()

        # TODO! this is also a horrible antipattern here, the handling of the browser session should be decoupled from the navigator

        # Create browser session with isolation
        browser_profile = BrowserProfile(
            # ? these None settings are necessary in order for every new run to be perfectly independent and clean
            storage_state=None,
            # Apply browser configuration if available
            **self.replay_traversal.browser_config.model_dump(exclude_none=True),
            args=["--no-sandbox", "--disable-setuid-sandbox"],
            record_video_dir="./recordings",  # Directory to save .webm video files
        )

        # Override user_data_dir with run_id for browser isolation
        base_dir = browser_profile.user_data_dir or Path("./data_dir")
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        isolated_dir = base_dir / f"run_{self.run_id}"
        browser_profile.user_data_dir = isolated_dir

        self.browser_session = BrowserSession(browser_profile=browser_profile)

        logger.bugninja_log(f"🔒 Using isolated browser directory: {isolated_dir}")

    async def _handle_go_to_url(self, action: Dict[str, Any]) -> None:
        """Handle navigation to a URL."""
        url = action["go_to_url"]["url"]
        logger.bugninja_log(f"🌐 Navigating to URL: {url}")

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                await self.current_page.goto(url, wait_until="load")
                return
            except Exception as e:
                if "net::ERR_NETWORK_CHANGED" in str(e) and attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ Network error occurred, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

    async def _handle_click(self, element_info: Optional[Dict[str, Any]]) -> None:
        """Handle clicking an element."""

        if not element_info:
            raise ActionError("No element information provided for event 'click'!")

        await self._execute_with_fallback("click", element_info)

    async def _handle_input_text(
        self, action: Dict[str, Any], element_info: Optional[Dict[str, Any]]
    ) -> None:
        """Handle text input."""

        if not element_info:
            raise ActionError("No element information provided for event 'fill'!")

        await self._execute_with_fallback(
            "fill", element_info, {"text": action["input_text"]["text"]}
        )

    async def _handle_extract_content(self) -> None:
        """Handle content extraction."""
        logger.bugninja_log("📋 Content extraction requested")
        await self.__handle_not_implemented_action("Content extraction")

    async def _handle_wait(self) -> None:
        """Handle waiting."""
        logger.bugninja_log("⏳ Waiting requested")
        await self.__handle_not_implemented_action("Waiting functionality")

    async def _handle_go_back(self) -> None:
        """Handle navigation back."""
        logger.bugninja_log("⬅️ Go back requested")
        await self.__handle_not_implemented_action("Back navigation")

    async def _handle_search_google(self) -> None:
        """Handle Google search."""
        logger.bugninja_log("🔍 Google search requested")
        await self.__handle_not_implemented_action("Google search")

    async def _handle_save_pdf(self) -> None:
        """Handle PDF saving."""
        logger.bugninja_log("📄 PDF save requested")
        await self.__handle_not_implemented_action("PDF saving")

    async def _handle_switch_tab(self, switch_tab_id: Optional[int]) -> None:
        """Handle tab switching."""
        logger.bugninja_log("🔄 Tab switch requested")

        #! precautionary sleep, so that the tab has time to load
        await asyncio.sleep(1)

        if switch_tab_id is None:
            raise ActionError("No page ID provided for tab switching")

        contexts: Sequence[PatchrightBrowserContext] = self.browser_session.browser.contexts

        if not len(contexts):
            raise ActionError("No browser contexts found for tab switching")

        current_context: PatchrightBrowserContext = contexts[0]

        if not len(current_context.pages):
            raise ActionError("No pages found for tab switching")

        self.current_page: Page = current_context.pages[switch_tab_id]

        await self.current_page.bring_to_front()

    async def _handle_open_tab(self) -> None:
        """Handle opening new tab."""
        logger.bugninja_log("➕ New tab requested")
        await self.__handle_not_implemented_action("New tab")

    async def _handle_close_tab(self) -> None:
        """Handle closing tab."""
        logger.bugninja_log("❌ Tab close requested")
        await self.__handle_not_implemented_action("Tab closing")

    async def _handle_get_ax_tree(self) -> None:
        """Handle getting accessibility tree."""
        logger.bugninja_log("🌳 Accessibility tree requested")
        await self.__handle_not_implemented_action("Accessability tree request")

    async def _scroll(self, scroll_amount: Optional[int], how: Literal["up", "down"]) -> None:
        """Handle scrolling to a specific direction."""
        logger.bugninja_log(f"⬇️ Scroll {how} requested")
        """
			(a) Use browser._scroll_container for container-aware scrolling.
			(b) If that JavaScript throws, fall back to window.scrollBy().
		"""

        dy = scroll_amount or await self.current_page.evaluate("() => window.innerHeight")

        if how == "up":
            dy = -dy

        await self.current_page.wait_for_timeout(500)

        await self.current_page.evaluate("(y) => window.scrollBy(0, y)", dy)
        logger.bugninja_log(f"🔍 Scrolled down the page by {dy} pixels")

    async def _handle_scroll_down(self, scroll_amount: Optional[int]) -> None:
        """Handle scrolling down."""
        await self._scroll(scroll_amount, "down")

    async def _handle_scroll_up(self, scroll_amount: Optional[int]) -> None:
        """Handle scrolling up."""
        await self._scroll(scroll_amount, "up")

    async def _handle_send_keys(self) -> None:
        """Handle sending keys."""
        logger.bugninja_log("⌨️ Send keys requested")
        await self.__handle_not_implemented_action("Send keys")

    async def _handle_scroll_to_text(self) -> None:
        """Handle scrolling to text."""
        logger.bugninja_log("🔍 Scroll to text requested")
        await self.__handle_not_implemented_action("Scroll to text")

    async def _handle_get_dropdown_options(self) -> None:
        """Handle getting dropdown options."""
        logger.bugninja_log("📝 Dropdown options requested")
        await self.__handle_not_implemented_action("Dropdown options")

    async def _handle_select_dropdown_option(self) -> None:
        """Handle selecting dropdown option."""
        logger.bugninja_log("✅ Dropdown selection requested")
        await self.__handle_not_implemented_action("Dropdown selection")

    async def _handle_drag_drop(self) -> None:
        """Handle drag and drop."""
        logger.bugninja_log("🔄 Drag and drop requested")
        await self.__handle_not_implemented_action("Drag and drop")

    async def _handle_done(self) -> None:
        """Handle done action."""
        logger.bugninja_log("✅ Done action received")

    async def _execute_with_fallback(
        self,
        action_type: str,
        element_info: Dict[str, Any],
        action_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute an action with selector fallback mechanism.

        Args:
            action_type: Type of action to perform ('click' or 'fill')
            element_info: Information about the element to interact with
            action_kwargs: Additional arguments for the action

        Raises:
            ActionError: If the action fails after trying all selectors
        """
        if not element_info:
            raise ActionError("No element information provided")

        selectors = await self._get_element_selector(element_info)
        logger.bugninja_log(
            f"🖱️ Attempting to {action_type} element with {len(selectors)} selectors"
        )

        last_error = None
        for selector_type, selector in selectors:
            logger.bugninja_log(f"🔄 Trying {selector_type} selector: {selector}")
            success, error = await self._try_selector(
                self.current_page, selector, action_type, **(action_kwargs or {})
            )

            if success:
                logger.bugninja_log(
                    f"✅ Successfully {action_type}ed element using {selector_type} selector"
                )
                return

            last_error = error
            logger.warning(f"⚠️ Selector failed: {error}")

        # If we get here, all selectors failed
        failed_selectors = [f"{type}: {sel}" for type, sel in selectors]
        error_msg = (
            f"Failed to {action_type} element. "
            f"Tried selectors: {', '.join(failed_selectors)}. "
            f"Last error: {last_error}"
        )
        raise ActionError(error_msg)

    async def __handle_not_implemented_action(self, feature_name: str) -> None:
        if self.fail_on_unimplemented_action:
            raise ActionError(f"{feature_name} not yet implemented")

    async def _get_element_selector(self, element_info: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Get a list of selectors for an element based on available information.
        Returns selectors in priority order: Primary XPath, then alternative relative XPaths.

        Args:
            element_info: Dictionary containing element information

        Returns:
            List of tuples containing (selector_type, selector_value)

        Raises:
            SelectorError: If no valid selectors can be generated
        """
        selectors = []

        # Add primary XPath if available
        if element_info.get("xpath"):
            selectors.append(("xpath", element_info["xpath"]))
            logger.debug(f"🎯 Added primary XPath selector: {element_info['xpath']}")

        # Add alternative relative XPaths if available
        if element_info.get("alternative_relative_xpaths"):
            for xpath in element_info["alternative_relative_xpaths"]:
                selectors.append(("xpath", xpath))
                logger.debug(f"🎯 Added alternative XPath selector: {xpath}")

        # If no selectors were found, try to construct a basic selector
        if not selectors:
            tag = element_info.get("tag_name", "")
            attrs = element_info.get("attributes", {})

            if not tag:
                raise SelectorError("No valid selector information available")

            # Construct a valid CSS selector
            if attrs:
                attr_pairs = [f"{k}='{v}'" for k, v in attrs.items()]
                selector = f"{tag}[{', '.join(attr_pairs)}]"
            else:
                selector = tag

            selectors.append(("css", selector))
            logger.debug(f"🎯 Using fallback selector: {selector}")

        return selectors

    async def _execute_action(self, interaction: BugninjaExtendedAction) -> None:
        """
        Execute a single interaction's action using Patchright with retry mechanism.

        Args:
            interaction: Dictionary containing the interaction information

        Raises:
            ActionError: If the action fails after all retries
        """

        # Log brain information before executing the action
        brain: Optional[AgentBrain] = self.brain_states.get(interaction.brain_state_id)

        if not brain:
            error_msg = f"🚫 No brain information found for interaction: {interaction}"
            logger.error(error_msg)
            raise ActionError(error_msg)

        logger.bugninja_log("\n")
        logger.bugninja_log("🧠 Current State:")
        logger.bugninja_log(f"📝 Memory: {brain.memory}")
        logger.bugninja_log(f"🎯 Next Goal: {brain.next_goal}")
        logger.bugninja_log(f"✅ Previous Evaluation: {brain.evaluation_previous_goal}")
        logger.bugninja_log("=" * 20)

        # TODO! Do here a major refactor with a lot of custom schemas,
        #! otherwise dictionary drilling will be pain and also makes the code hard to debug

        element_info: Optional[Dict[str, Any]] = interaction.dom_element_data

        switch_tab_action: Optional[Dict[str, Any]] = interaction.action.get("switch_tab")
        scroll_down_action: Optional[Dict[str, Any]] = interaction.action.get("scroll_down")
        scroll_up_action: Optional[Dict[str, Any]] = interaction.action.get("scroll_down")

        scroll_amount: Optional[int] = None
        switch_tab_id: Optional[int] = None

        if switch_tab_action:
            switch_tab_id = switch_tab_action["tab_id"]

        if scroll_down_action:
            scroll_amount = scroll_down_action["amount"]

        if scroll_up_action:
            scroll_amount = scroll_up_action["amount"]

        # Map actions to their handlers
        action_handlers = {
            "go_to_url": lambda: self._handle_go_to_url(action=interaction.action),
            "click_element_by_index": lambda: self._handle_click(element_info=element_info),
            "input_text": lambda: self._handle_input_text(
                action=interaction.action, element_info=element_info
            ),
            "extract_content": self._handle_extract_content,
            "wait": self._handle_wait,
            "go_back": self._handle_go_back,
            "search_google": self._handle_search_google,
            "save_pdf": self._handle_save_pdf,
            "switch_tab": lambda: self._handle_switch_tab(switch_tab_id=switch_tab_id),
            "open_tab": self._handle_open_tab,
            "close_tab": self._handle_close_tab,
            "get_ax_tree": self._handle_get_ax_tree,
            "scroll_down": lambda: self._handle_scroll_down(scroll_amount=scroll_amount),
            "scroll_up": lambda: self._handle_scroll_up(scroll_amount=scroll_amount),
            "send_keys": self._handle_send_keys,
            "scroll_to_text": self._handle_scroll_to_text,
            "get_dropdown_options": self._handle_get_dropdown_options,
            "select_dropdown_option": self._handle_select_dropdown_option,
            "drag_drop": self._handle_drag_drop,
            "done": self._handle_done,
        }

        # Get the appropriate handler for the action
        non_none_action: Dict[str, Any] = {
            k: v for k, v in interaction.action.items() if v is not None
        }

        handler = action_handlers.get(list(non_none_action.keys())[0])

        if handler:
            await handler()
            #! precautionary sleep so that the replay function has time to catch up
            await asyncio.sleep(self.sleep_after_actions)
        else:
            raise ActionError(f"Unknown action type: {interaction.action}")

    async def _try_selector(
        self, page: Page, selector: str, action: str, **kwargs: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to execute an action with a specific selector.

        Args:
            page: The page to execute the action on
            selector: The selector to use
            action: The action to perform ('click', 'fill', etc.)
            **kwargs: Additional arguments for the action

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        # Wait for page to be fully loaded
        await page.wait_for_load_state("load")
        await page.wait_for_load_state("domcontentloaded")

        logger.bugninja_log(f"📝 Using selector: {selector}")

        try:
            # Get element and verify its state
            element = page.locator(selector)

            await element.wait_for(state="attached", timeout=1000)

            element_count = await element.count()
            logger.bugninja_log(f"Found '{element_count}' elements for selector")

            if element_count == 0:
                logger.warning(f"⚠️ No elements found for selector: {selector}")
                return False, f"No elements found for selector: {selector}"
            if element_count > 1:
                logger.warning(f"⚠️ Multiple elements found for selector: {selector}")
                return False, f"Multiple elements found for selector: {selector}"

            if action == "click":
                await element.click()
            elif action == "fill":
                value: Optional[str] = kwargs.get("text")  # type:ignore

                if value is None:
                    logger.warning(f"⚠️ No value provided for {action} action")
                    return False, "No value provided for fill action"

                for key, secret_value in self.secrets.items():
                    secret_key = f"<secret>{key}</secret>"
                    if secret_key in value:
                        value = value.replace(f"<secret>{key}</secret>", secret_value)

                await element.fill(value)
            return True, None
        except Exception as e:
            error_msg = f"Failed to {action} with selector {selector}: {str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            return False, error_msg

    async def cleanup(self) -> None:
        """
        Clean up resources after execution.

        This method closes the browser and playwright instance.
        """

        if self.current_page:
            await self.current_page.close()
            logger.debug("✅ Page closed")
        if self.browser_session.browser:
            await self.browser_session.browser.close()
            logger.debug("✅ Browser closed")
        if self.browser_session.playwright:
            await self.browser_session.playwright.stop()
            logger.debug("✅ Playwright stopped")

        await self.browser_session.close()

        gc.collect()

        logger.bugninja_log("✨ Cleanup completed")

    async def before_run(self) -> None:
        logger.bugninja_log("🚀 Starting browser session")
        await self.browser_session.start()
        self.current_page = await self.browser_session.get_current_page()

    async def after_run(self, did_run_fail: bool, failed_reason: Optional[str]) -> None:

        logger.bugninja_log("🧹 Cleaning up resources")
        await self.cleanup()

        if did_run_fail:
            logger.error("❌ Replication failed")
            raise ReplicatorError(failed_reason)
        else:
            logger.bugninja_log("✅ Replication completed successfully")

    async def start(self) -> None:
        """
        Start the replication process

        Raises:
            NotImplementedError: The run method must be implemented
        """

        await self.before_run()

        failed_reason: Optional[str]

        success, failed_reason = await self._run()

        await self.after_run(did_run_fail=not success, failed_reason=failed_reason)

    async def _run(self) -> Tuple[bool, Optional[str]]:
        """This function describes what should happen during the replication of the replay.

        **In ideal scenario**:

        Run through all steps in the JSON file and execute them.

        This method should process each interaction sequentially, executing the
        corresponding browser action for each interaction. If an action fails,
        it attempts self-healing before continuing or failing the replication.

        Raises:
            NotImplementedError: The functionality of the run method must be implemented

        Returns:
            Tuple[bool, Optional[str]]: Returns a tuple of a boolean and an optional string, which indicates whether the run was successful and,
            if not, the reason for the failure.
        """
        raise NotImplementedError(
            "The run method must be implemented in order for the class to be able to run"
        )
