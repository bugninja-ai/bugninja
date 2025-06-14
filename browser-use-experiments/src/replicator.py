"""
Browser Interaction Replicator

This module implements a class that can read and execute browser interactions
from a JSON log file. It processes each interaction sequentially and performs the
corresponding browser actions using Patchright (undetected Playwright).

The JSON log file contains steps with:
- model_taken_action: The action to perform
- interacted_element: Details about the element to interact with
- brain: Agent's reasoning and state
- action_details: Specific details about the action
"""

from typing import Dict, Any, List, Tuple, Optional
import json
import asyncio
import logging
from pathlib import Path
from patchright.async_api import Page, async_playwright
from rich import print as rich_print
from patchright.async_api import BrowserContext as PatchrightBrowserContext

# Configure logging with custom format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ReplicatorError(Exception):
    """Base exception for Replicator errors."""

    pass


class SelectorError(ReplicatorError):
    """Exception raised when selector operations fail."""

    pass


class ActionError(ReplicatorError):
    """Exception raised when browser actions fail."""

    pass


class Replicator:
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
        secrets: Dict[str, str] = {},
    ):
        """
        Initialize the Replicator with a JSON file path.

        Args:
            json_path: Path to the JSON file containing interaction steps
        """
        self.json_path = Path(json_path)
        self.replay_json = self._load_json()
        self.current_interaction = 0
        self.playwright = None
        self.browser = None
        self.current_page = None
        self.max_retries = 2
        self.retry_delay = 0.5
        self.sleep_after_actions = sleep_after_actions
        self.failed = False
        self.failed_reason: Optional[Exception] = None
        self.secrets = secrets
        logger.info(
            f"🚀 Initialized Replicator with {len(self.replay_json.get('interactions', []))} steps to process"
        )

        self.fail_on_unimplemented_action = fail_on_unimplemented_action

    def _load_json(self) -> Dict[str, Any]:
        """
        Load and parse the JSON file containing interaction steps.

        Returns:
            Dict containing the parsed JSON data
        """
        try:
            with open(self.json_path, "r") as f:
                data = json.load(f)
                if "interactions" not in data:
                    raise ReplicatorError("JSON file must contain an 'interactions' key")
                logger.info(f"📄 Successfully loaded JSON file: {self.json_path}")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load JSON file: {str(e)}")
            raise ReplicatorError(f"Failed to load JSON file: {str(e)}")

    async def _try_selector(
        self, page: Page, selector: str, action: str, selector_type: str, **kwargs
    ) -> bool:
        """
        Try to execute an action with a specific selector.

        Args:
            page: The page to execute the action on
            selector: The selector to use
            action: The action to perform ('click', 'fill', etc.)
            selector_type: The type of selector ('xpath', 'css', etc.)
            **kwargs: Additional arguments for the action

        Returns:
            bool: True if action succeeded, False otherwise
        """
        # Wait for page to be fully loaded
        await page.wait_for_load_state("load")
        await page.wait_for_load_state("domcontentloaded")

        logger.info(f"📝 Using selector: {selector}")

        # Get element and verify its state
        element = page.locator(selector)
        await element.wait_for(state="attached", timeout=5000000)

        logger.info(f"Found '{await element.count()}' elements for selector")

        try:
            if action == "click":
                await element.click()
            elif action == "fill":
                value: Optional[str] = kwargs.get("text")

                if value is None:
                    logger.warning(f"⚠️ No value provided for {action} action")
                    return False

                for key, secret_value in self.secrets.items():
                    secret_key = f"<secret>{key}</secret>"
                    if secret_key in value:
                        value = value.replace(f"<secret>{key}</secret>", secret_value)

                await element.fill(value)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to {action} with selector {selector}: {str(e)}")
            return False

    async def _get_element_selector(self, element_info: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Get a list of selectors for an element based on available information.
        Returns selectors in priority order: XPath, Improved XPath, CSS, Improved CSS.

        Args:
            element_info: Dictionary containing element information

        Returns:
            List of tuples containing (selector_type, selector_value)

        Raises:
            SelectorError: If no valid selectors can be generated
        """
        selectors = []

        # Add original XPath if available
        if element_info.get("xpath"):
            selectors.append(("xpath", element_info["xpath"]))
            logger.debug(f"🎯 Added XPath selector: {element_info['xpath']}")

        # Add improved XPath if available
        if element_info.get("improved_xpath_selector"):
            selectors.append(("xpath", element_info["improved_xpath_selector"]))
            logger.debug(
                f"🎯 Added improved XPath selector: {element_info['improved_xpath_selector']}"
            )

        # Add original CSS selector if available
        if element_info.get("css_selector"):
            selectors.append(("css", element_info["css_selector"]))
            logger.debug(f"🎯 Added CSS selector: {element_info['css_selector']}")

        # Add improved CSS selector if available
        if element_info.get("improved_css_selector"):
            selectors.append(("css", element_info["improved_css_selector"]))
            logger.debug(f"🎯 Added improved CSS selector: {element_info['improved_css_selector']}")

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

    async def _execute_with_retry(
        self,
        action_type: str,
        element_info: Dict[str, Any],
        action_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute an action with retry mechanism and selector fallback.

        Args:
            action_type: Type of action to perform ('click' or 'fill')
            element_info: Information about the element to interact with
            action_kwargs: Additional arguments for the action

        Raises:
            ActionError: If the action fails after all retries
        """
        selectors = await self._get_element_selector(element_info)
        logger.info(f"🖱️ Attempting to {action_type} element with {len(selectors)} selectors")

        for attempt in range(self.max_retries):
            for selector_type, selector in selectors:
                logger.info(f"🔄 Trying {selector_type} selector: {selector}")
                if await self._try_selector(
                    self.current_page, selector, action_type, selector_type, **(action_kwargs or {})
                ):
                    logger.info(
                        f"✅ Successfully {action_type}ed element using {selector_type} selector"
                    )
                    return

            if attempt < self.max_retries - 1:
                logger.warning(
                    f"🔄 Retry {attempt + 1}/{self.max_retries} for {action_type} action - all selectors failed"
                )
                await asyncio.sleep(self.retry_delay)

        # If we get here, all selectors failed after all retries
        failed_selectors = [f"{type}: {sel}" for type, sel in selectors]
        raise ActionError(
            f"Failed to {action_type} element after {self.max_retries} attempts. "
            f"Tried selectors: {', '.join(failed_selectors)}"
        )

    async def _handle_go_to_url(self, action: Dict[str, Any]) -> None:
        """Handle navigation to a URL."""
        url = action["go_to_url"]["url"]
        logger.info(f"🌐 Navigating to URL: {url}")

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

    async def _handle_click(self, element_info: Dict[str, Any]) -> None:
        """Handle clicking an element."""
        await self._execute_with_retry("click", element_info)

    async def _handle_input_text(
        self, action: Dict[str, Any], element_info: Dict[str, Any]
    ) -> None:
        """Handle text input."""
        text = action["input_text"]["text"]
        await self._execute_with_retry("fill", element_info, {"text": text})

    async def __handle_not_implemented_action(self, feature_name: str) -> None:
        if self.fail_on_unimplemented_action:
            raise ActionError(f"{feature_name} not yet implemented")

    async def _handle_extract_content(self) -> None:
        """Handle content extraction."""
        logger.info("📋 Content extraction requested")
        await self.__handle_not_implemented_action("Content extraction")

    async def _handle_wait(self) -> None:
        """Handle waiting."""
        logger.info("⏳ Waiting requested")
        await self.__handle_not_implemented_action("Waiting functionality")

    async def _handle_go_back(self) -> None:
        """Handle navigation back."""
        logger.info("⬅️ Go back requested")
        await self.__handle_not_implemented_action("Back navigation")

    async def _handle_search_google(self) -> None:
        """Handle Google search."""
        logger.info("🔍 Google search requested")
        await self.__handle_not_implemented_action("Google search")

    async def _handle_save_pdf(self) -> None:
        """Handle PDF saving."""
        logger.info("📄 PDF save requested")
        await self.__handle_not_implemented_action("PDF saving")

    async def _handle_switch_tab(self, switch_tab_id: Optional[int]) -> None:
        """Handle tab switching."""
        logger.info("🔄 Tab switch requested")

        #! precautionary sleep, so that the tab has time to load
        await asyncio.sleep(1)

        if switch_tab_id is None:
            raise ActionError("No page ID provided for tab switching")

        contexts: List[PatchrightBrowserContext] = self.browser.contexts

        if not len(contexts):
            raise ActionError("No browser contexts found for tab switching")

        current_context: PatchrightBrowserContext = contexts[0]

        if not len(current_context.pages):
            raise ActionError("No pages found for tab switching")

        self.current_page = current_context.pages[switch_tab_id]

        await self.current_page.bring_to_front()

    async def _handle_open_tab(self) -> None:
        """Handle opening new tab."""
        logger.info("➕ New tab requested")
        await self.__handle_not_implemented_action("New tab")

    async def _handle_close_tab(self) -> None:
        """Handle closing tab."""
        logger.info("❌ Tab close requested")
        await self.__handle_not_implemented_action("Tab closing")

    async def _handle_get_ax_tree(self) -> None:
        """Handle getting accessibility tree."""
        logger.info("🌳 Accessibility tree requested")
        await self.__handle_not_implemented_action("Accessability tree request")

    async def _scroll(self, how: str) -> None:
        """Handle scrolling to a specific direction."""

        logger.info(f"⬇️ Scroll {how} requested")
        """
			(a) Use browser._scroll_container for container-aware scrolling.
			(b) If that JavaScript throws, fall back to window.scrollBy().
		"""
        dy = await self.current_page.evaluate("() => window.innerHeight")

        rich_print(f"DY: {dy}")

        if how == "up":
            dy = -dy

        try:

            await self.current_page.wait_for_timeout(500)
            await self.current_page.mouse.wheel(0, dy)
            await self.current_page.wait_for_timeout(500)

        except Exception as e:
            # Hard fallback: always works on root scroller
            await self.current_page.evaluate("(y) => window.scrollBy(0, y)", dy)
            logger.debug("Smart scroll failed; used window.scrollBy fallback", exc_info=e)

        msg = f"🔍 Scrolled {how} the page by one page"
        logger.info(msg)

    async def _handle_scroll_down(self) -> None:
        """Handle scrolling down."""
        await self._scroll("down")

    async def _handle_scroll_up(self) -> None:
        """Handle scrolling up."""
        await self._scroll("up")

    async def _handle_send_keys(self) -> None:
        """Handle sending keys."""
        logger.info("⌨️ Send keys requested")
        await self.__handle_not_implemented_action("Send keys")

    async def _handle_scroll_to_text(self) -> None:
        """Handle scrolling to text."""
        logger.info("🔍 Scroll to text requested")
        await self.__handle_not_implemented_action("Scroll to text")

    async def _handle_get_dropdown_options(self) -> None:
        """Handle getting dropdown options."""
        logger.info("📝 Dropdown options requested")
        await self.__handle_not_implemented_action("Dropdown options")

    async def _handle_select_dropdown_option(self) -> None:
        """Handle selecting dropdown option."""
        logger.info("✅ Dropdown selection requested")
        await self.__handle_not_implemented_action("Dropdown selection")

    async def _handle_drag_drop(self) -> None:
        """Handle drag and drop."""
        logger.info("🔄 Drag and drop requested")
        await self.__handle_not_implemented_action("Drag and drop")

    async def _handle_done(self) -> None:
        """Handle done action."""
        logger.info("✅ Done action received")
        # This is a status indicator, not an error
        return

    #! The 'can_be_skipped flag has been added for a specific reason.
    #! If there are steps taken by the original AI agent that do not necessarily contribute for the completion of the whole flow, the specific element can be skipped.
    #! Right now, we do not have a solution to automatically map which steps of specific flows can be or should be skipped, but in the upcoming features,
    #! I will most likely develop an AI agent solution for this.

    async def _execute_action(self, interaction: Dict[str, Any], can_be_skipped: bool) -> None:
        """
        Execute a single interaction's action using Patchright with retry mechanism.

        Args:
            interaction: Dictionary containing the interaction information
            can_be_skipped: Whether this interaction can be skipped

        Raises:
            ActionError: If the action fails after all retries
        """
        if can_be_skipped:
            logger.info(f"📝 Skipping interaction: {interaction['model_taken_action']}")
            return

        # Log brain information before executing the action
        brain = interaction.get("brain", {})
        memory = brain.get("memory", "No memory information available")
        next_goal = brain.get("next_goal", "No goal information available")

        logger.info("\n")
        logger.info("🧠 Current State:")
        logger.info(f"📝 Memory: {memory}")
        logger.info(f"🎯 Next Goal: {next_goal}")
        logger.info("=" * 20)

        action: Dict[str, Any] = interaction["model_taken_action"]
        element_info: Dict[str, Any] = action.get("interacted_element", {})
        switch_tab_id: Optional[int] = action.get("switch_tab", {}).get("page_id", None)

        # Map actions to their handlers
        action_handlers = {
            "go_to_url": lambda: self._handle_go_to_url(action=action),
            "click_element_by_index": lambda: self._handle_click(element_info=element_info),
            "input_text": lambda: self._handle_input_text(action=action, element_info=element_info),
            "extract_content": self._handle_extract_content,
            "wait": self._handle_wait,
            "go_back": self._handle_go_back,
            "search_google": self._handle_search_google,
            "save_pdf": self._handle_save_pdf,
            "switch_tab": lambda: self._handle_switch_tab(switch_tab_id=switch_tab_id),
            "open_tab": self._handle_open_tab,
            "close_tab": self._handle_close_tab,
            "get_ax_tree": self._handle_get_ax_tree,
            "scroll_down": self._handle_scroll_down,
            "scroll_up": self._handle_scroll_up,
            "send_keys": self._handle_send_keys,
            "scroll_to_text": self._handle_scroll_to_text,
            "get_dropdown_options": self._handle_get_dropdown_options,
            "select_dropdown_option": self._handle_select_dropdown_option,
            "drag_drop": self._handle_drag_drop,
            "done": self._handle_done,
        }

        # Get the appropriate handler for the action
        handler = action_handlers.get(next(iter(action.keys())))
        if handler:
            await handler()
            #! precautionary sleep so that the replay function has time to catch up
            await asyncio.sleep(self.sleep_after_actions)
        else:
            raise ActionError(f"Unknown action type: {action}")

    async def run(self, can_be_skipped_steps_list: List[int] = []) -> None:
        """
        Run through all steps in the JSON file and execute them.

        This method processes each interaction sequentially, executing the
        corresponding browser action for each interaction.
        """
        try:
            logger.info("🚀 Starting browser session")
            self.playwright = await async_playwright().start()

            # Apply browser configuration if available
            browser_config: Dict[str, Any] = self.replay_json.get("browser_config", {})

            # Launch browser with basic options
            self.browser = await self.playwright.chromium.launch(headless=False)

            # Prepare context options with proper defaults
            # Remove None values to avoid Playwright errors
            context_options = {
                k: v
                for k, v in {
                    "viewport": browser_config.get("viewport"),
                    "user_agent": browser_config.get("user_agent"),
                    "java_script_enabled": browser_config.get("java_script_enabled", True),
                    "accept_downloads": browser_config.get("accept_downloads", True),
                    "extra_http_headers": browser_config.get("extra_http_headers", {}),
                    "http_credentials": browser_config.get("http_credentials"),
                    "color_scheme": browser_config.get("color_scheme", "light"),
                    "device_scale_factor": browser_config.get("device_scale_factor"),
                    "geolocation": browser_config.get("geolocation"),
                    "proxy": browser_config.get("proxy"),
                    "client_certificates": browser_config.get("client_certificates", []),
                }.items()
                if v is not None
            }

            # Create context with all configurations
            context = await self.browser.new_context(**context_options)
            self.current_page = await context.new_page()
            self.current_page.set_default_timeout(browser_config.get(5000))

            for idx, (interaction_name, interaction_data) in enumerate(
                self.replay_json["interactions"].items()
            ):
                logger.info(f"📝 Executing interaction: {interaction_name}")
                try:
                    await self._execute_action(
                        interaction_data, can_be_skipped=idx in can_be_skipped_steps_list
                    )
                    self.current_interaction += 1
                except (SelectorError, ActionError) as e:
                    logger.error(f"❌ Error in interaction {interaction_name}: {str(e)}")
                    self.failed = True
                    break

        except Exception as e:
            logger.error(f"❌ Error executing interaction {self.current_interaction}: {str(e)}")
            self.failed = True
            self.failed_reason = e

        finally:
            logger.info("🧹 Cleaning up resources")
            await self.cleanup()

            if self.failed:
                logger.error("❌ Replication failed")
                raise Exception(self.failed_reason)
            else:
                logger.info("✅ Replication completed successfully")

    async def cleanup(self) -> None:
        """
        Clean up resources after execution.

        This method closes the browser and playwright instance.
        """
        if self.current_page:
            await self.current_page.close()
            logger.debug("✅ Page closed")
        if self.browser:
            await self.browser.close()
            logger.debug("✅ Browser closed")
        if self.playwright:
            await self.playwright.stop()
            logger.debug("✅ Playwright stopped")
        logger.info("✨ Cleanup completed")
