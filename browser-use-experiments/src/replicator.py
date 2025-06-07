"""
Browser Interaction Replicator

This module implements a class that can read and execute browser interactions
from a JSON log file. It processes each step sequentially and performs the
corresponding browser actions using Patchright (undetected Playwright).

The JSON log file contains steps with:
- model_taken_action: The action to perform
- interacted_element: Details about the element to interact with
- brain: Agent's reasoning and state
- action_details: Specific details about the action
"""

from typing import Dict, Any, List, Tuple
import json
import asyncio
import logging
from pathlib import Path
from patchright.async_api import Page, async_playwright
from rich import print as rich_print

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
    executes them sequentially using Patchright. Each step is processed
    and the corresponding browser action is performed with fallback mechanisms
    for element selection.
    """

    def __init__(self, json_path: str):
        """
        Initialize the Replicator with a JSON file path.

        Args:
            json_path: Path to the JSON file containing interaction steps
        """
        self.json_path = Path(json_path)
        self.steps = self._load_json()
        self.current_step = 0
        self.playwright = None
        self.browser = None
        self.page = None
        self.max_retries = 5  # Increased to 5 retries
        self.retry_delay = 1  # seconds
        self.failed = False
        logger.info(f"🚀 Initialized Replicator with {len(self.steps)} steps to process")

    def _load_json(self) -> Dict[str, Any]:
        """
        Load and parse the JSON file containing interaction steps.

        Returns:
            Dict containing the parsed JSON data
        """
        try:
            with open(self.json_path, "r") as f:
                data = json.load(f)
                logger.info(f"📄 Successfully loaded JSON file: {self.json_path}")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load JSON file: {str(e)}")
            raise ReplicatorError(f"Failed to load JSON file: {str(e)}")

    async def _try_selector(self, page: Page, selector: str, action: str, **kwargs) -> bool:
        """
        Try to execute an action with a specific selector.

        Args:
            page: The page to execute the action on
            selector: The selector to use
            action: The action to perform ('click', 'fill', etc.)
            **kwargs: Additional arguments for the action

        Returns:
            bool: True if action succeeded, False otherwise
        """
        try:
            if action == "click":
                await page.click(selector)
            elif action == "fill":
                await page.fill(selector, kwargs.get("text", ""))
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to {action} with selector {selector}: {str(e)}")
            return False

    async def _get_element_selector(self, element_info: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get the best selector for an element based on available information.
        Prioritizes XPath over CSS selector.

        Args:
            element_info: Dictionary containing element information

        Returns:
            Tuple of (selector_type, selector_value)

        Raises:
            SelectorError: If no valid selector can be generated
        """

        rich_print(element_info)

        # First try XPath
        if element_info.get("xpath"):
            logger.debug(f"🎯 Using XPath selector: {element_info['xpath']}")
            return ("xpath", element_info["xpath"])

        # Fall back to CSS selector
        if element_info.get("css_selector"):
            logger.debug(f"🎯 Using CSS selector: {element_info['css_selector']}")
            return ("css", element_info["css_selector"])

        # Last resort: try to construct a selector from tag and attributes
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

        logger.debug(f"🎯 Using fallback selector: {selector}")
        return ("css", selector)

    #! The 'can_be_skipped flag has been added for a specific reason.
    #! If there are steps taken by the original AI agent that do not necessarily contribute for the completion of the whole flow, the specific element can be skipped.
    #! Right now, we do not have a solution to automatically map which steps of specific flows can be or should be skipped, but in the upcoming features,
    #! I will most likely develop an AI agent solution for this.

    async def _execute_action(self, step: Dict[str, Any], can_be_skipped: bool) -> None:
        """
        Execute a single step's action using Patchright with retry mechanism.

        Args:
            step: Dictionary containing the step information
            can_be_skipped: Whether this step can be skipped

        Raises:
            ActionError: If the action fails after all retries
        """

        if can_be_skipped:
            logger.info(f"📝 Skipping step: {step['model_taken_action']}")
            return

        action = step["model_taken_action"]
        element_info = action.get("interacted_element", {})

        # Handle different action types
        if "go_to_url" in action:
            url = action["go_to_url"]["url"]
            logger.info(f"🌐 Navigating to URL: {url}")
            await self.page.goto(url)

        elif "click_element_by_index" in action:
            selector_type, selector = await self._get_element_selector(element_info)
            logger.info(f"🖱️ Attempting to click element using {selector_type}")

            for attempt in range(self.max_retries):
                if await self._try_selector(self.page, selector, "click"):
                    logger.info(f"✅ Successfully clicked element using {selector_type}")
                    return

                if attempt < self.max_retries - 1:
                    logger.warning(f"🔄 Retry {attempt + 1}/{self.max_retries} for click action")
                    await asyncio.sleep(self.retry_delay)
                    # Try alternative selector if available
                    if selector_type == "xpath" and element_info.get("css_selector"):
                        selector = element_info["css_selector"]
                        selector_type = "css"
                        logger.info(f"🔄 Falling back to CSS selector: {selector}")
                    elif selector_type == "css" and element_info.get("xpath"):
                        selector = element_info["xpath"]
                        selector_type = "xpath"
                        logger.info(f"🔄 Falling back to XPath selector: {selector}")

            raise ActionError(f"Failed to click element after {self.max_retries} attempts")

        elif "input_text" in action:
            selector_type, selector = await self._get_element_selector(element_info)
            text = action["input_text"]["text"]
            logger.info(f"⌨️ Attempting to input text using {selector_type}")

            for attempt in range(self.max_retries):
                if await self._try_selector(self.page, selector, "fill", text=text):
                    logger.info(f"✅ Successfully filled text using {selector_type}")
                    return

                if attempt < self.max_retries - 1:
                    logger.warning(f"🔄 Retry {attempt + 1}/{self.max_retries} for text input")
                    await asyncio.sleep(self.retry_delay)
                    # Try alternative selector if available
                    if selector_type == "xpath" and element_info.get("css_selector"):
                        selector = element_info["css_selector"]
                        selector_type = "css"
                        logger.info(f"🔄 Falling back to CSS selector: {selector}")
                    elif selector_type == "css" and element_info.get("xpath"):
                        selector = element_info["xpath"]
                        selector_type = "xpath"
                        logger.info(f"🔄 Falling back to XPath selector: {selector}")

            raise ActionError(f"Failed to input text after {self.max_retries} attempts")

        elif "extract_content" in action:
            logger.info("📋 Content extraction requested")
            raise ActionError("Content extraction not yet implemented")

        elif "wait" in action:
            logger.info("⏳ Waiting requested")
            raise ActionError("Waiting functionality not yet implemented")

        elif "go_back" in action:
            logger.info("⬅️ Go back requested")
            raise ActionError("Navigation back functionality not yet implemented")

        elif "search_google" in action:
            logger.info("🔍 Google search requested")
            raise ActionError("Google search functionality not yet implemented")

        elif "save_pdf" in action:
            logger.info("📄 PDF save requested")
            raise ActionError("PDF saving functionality not yet implemented")

        elif "switch_tab" in action:
            logger.info("🔄 Tab switch requested")
            raise ActionError("Tab switching functionality not yet implemented")

        elif "open_tab" in action:
            logger.info("➕ New tab requested")
            raise ActionError("New tab functionality not yet implemented")

        elif "close_tab" in action:
            logger.info("❌ Tab close requested")
            raise ActionError("Tab closing functionality not yet implemented")

        elif "get_ax_tree" in action:
            logger.info("🌳 Accessibility tree requested")
            raise ActionError("Accessibility tree functionality not yet implemented")

        elif "scroll_down" in action:
            logger.info("⬇️ Scroll down requested")
            raise ActionError("Scroll down functionality not yet implemented")

        elif "scroll_up" in action:
            logger.info("⬆️ Scroll up requested")
            raise ActionError("Scroll up functionality not yet implemented")

        elif "send_keys" in action:
            logger.info("⌨️ Send keys requested")
            raise ActionError("Send keys functionality not yet implemented")

        elif "scroll_to_text" in action:
            logger.info("🔍 Scroll to text requested")
            raise ActionError("Scroll to text functionality not yet implemented")

        elif "get_dropdown_options" in action:
            logger.info("📝 Dropdown options requested")
            raise ActionError("Dropdown options functionality not yet implemented")

        elif "select_dropdown_option" in action:
            logger.info("✅ Dropdown selection requested")
            raise ActionError("Dropdown selection functionality not yet implemented")

        elif "drag_drop" in action:
            logger.info("🔄 Drag and drop requested")
            raise ActionError("Drag and drop functionality not yet implemented")

        elif "done" in action:
            logger.info("✅ Done action received")
            # This is a status indicator, not an error
            return

        else:
            raise ActionError(f"Unknown action type: {action}")

    async def run(self, can_be_skipped_steps_list: List[int]) -> None:
        """
        Run through all steps in the JSON file and execute them.

        This method processes each step sequentially, executing the
        corresponding browser action for each step.
        """
        try:
            logger.info("🚀 Starting browser session")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()

            for idx, (step_name, step_data) in enumerate(self.steps.items()):
                logger.info(f"📝 Executing step: {step_name}")
                try:
                    await self._execute_action(
                        step_data, can_be_skipped=idx in can_be_skipped_steps_list
                    )
                    self.current_step += 1
                except (SelectorError, ActionError) as e:
                    logger.error(f"❌ Error in step {step_name}: {str(e)}")
                    self.failed = True
                    break

        except Exception as e:
            logger.error(f"❌ Error executing step {self.current_step}: {str(e)}")
            self.failed = True

        finally:
            logger.info("🧹 Cleaning up resources")
            await self.cleanup()

            if self.failed:
                logger.error("❌ Replication failed")
                raise ReplicatorError("Replication failed")
            else:
                logger.info("✅ Replication completed successfully")

    async def cleanup(self) -> None:
        """
        Clean up resources after execution.

        This method closes the browser and playwright instance.
        """
        if self.page:
            await self.page.close()
            logger.debug("✅ Page closed")
        if self.browser:
            await self.browser.close()
            logger.debug("✅ Browser closed")
        if self.playwright:
            await self.playwright.stop()
            logger.debug("✅ Playwright stopped")
        logger.info("✨ Cleanup completed")
