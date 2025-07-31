import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from browser_use import BrowserSession  # type: ignore
from browser_use.browser.session import Page  # type: ignore

if TYPE_CHECKING:
    from bugninja.schemas.pipeline import BugninjaExtendedAction  # type: ignore

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Unified screenshot management for all agents and replay sessions."""

    def __init__(self, folder_prefix: str = "traversal"):
        """
        Initialize screenshot manager.

        Args:
            folder_prefix: Prefix for screenshot folders (traversal, replay, etc.)
        """
        self.folder_prefix = folder_prefix
        self.screenshots_dir = self._get_screenshots_dir()
        self.screenshots_dir.mkdir(exist_ok=True)
        self.screenshot_counter = 0
        logger.info(f"📸 Screenshots will be saved to: {self.screenshots_dir}")

    def _get_screenshots_dir(self) -> Path:
        """Get the screenshots directory for current session"""

        base_dir = Path("./screenshots")
        base_dir.mkdir(exist_ok=True)

        folder_number = 1
        while (base_dir / f"{self.folder_prefix}_{folder_number}").exists():
            folder_number += 1

        return base_dir / f"{self.folder_prefix}_{folder_number}"

    async def take_screenshot(
        self,
        page: Page,
        action: "BugninjaExtendedAction",
        browser_session: Optional[BrowserSession] = None,
    ) -> str:
        """
        Take screenshot and return filename.

        Args:
            page: Playwright page object (used to get context)
            action: Extended action containing DOM element data
            browser_session: Browser session object for taking screenshots

        Returns:
            Full relative path to screenshot file
        """
        self.screenshot_counter += 1

        # Extract XPath selectors and highlight element
        highlighted_element = None
        if action.dom_element_data:
            highlighted_element = await self._highlight_element_by_xpath(
                page, action.dom_element_data
            )

        # Generate filename
        action_data = action.model_dump(exclude_unset=True)
        action_type = list(action_data.keys())[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.screenshot_counter:03d}_{action_type}_{timestamp}.png"

        # Take screenshot using browser_session (captures entire browser window)
        if browser_session:
            screenshot_b64 = await browser_session.take_screenshot()

            # Convert base64 to PNG and save
            with open(self.screenshots_dir / filename, "wb") as f:
                f.write(base64.b64decode(screenshot_b64))
        else:
            # Fallback to page screenshot if no browser_session provided
            await page.screenshot(path=str(self.screenshots_dir / filename))

        # Remove highlight if element was highlighted
        if highlighted_element:
            await self._remove_highlight(page, highlighted_element)

        logger.info(f"📸 Screenshot: {filename}")

        # Return full relative path
        return f"screenshots/{self.screenshots_dir.name}/{filename}"

    async def _highlight_element_by_xpath(
        self, page: Page, dom_element_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Find and highlight element using XPath selectors.

        Args:
            page: Playwright page object
            dom_element_data: DOM element data containing XPath selectors

        Returns:
            XPath of the highlighted element, or None if no element found
        """
        # Get main XPath
        main_xpath: Optional[str] = dom_element_data.get("xpath")
        if not main_xpath:
            return None

        # Try main XPath first
        if await self._highlight_element_with_xpath(page, main_xpath):
            return main_xpath

        # Try alternative XPaths
        alternative_xpaths = dom_element_data.get("alternative_relative_xpaths", [])
        alt_xpath: str
        for alt_xpath in alternative_xpaths:
            if await self._highlight_element_with_xpath(page, alt_xpath):
                return alt_xpath

        return None

    async def _highlight_element_with_xpath(self, page: Page, xpath: str) -> bool:
        """
        Highlight element using specific XPath.

        Args:
            page: Playwright page object
            xpath: XPath selector to find and highlight

        Returns:
            True if element was found and highlighted, False otherwise
        """
        try:
            # Check if XPath resolves to exactly one element
            element_count = await page.evaluate(
                f"""
                () => {{
                    const result = document.evaluate('{xpath}', document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    return result.snapshotLength;
                }}
            """
            )

            if element_count != 1:
                return False

            # Highlight the element
            await page.evaluate(
                """
                (xpath) => {
                    const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (element) {
                        element.style.outline = '3px solid red';
                        element.setAttribute('data-highlighted', 'true');
                    }
                }
            """,
                xpath,
            )

            return True

        except Exception as e:
            logger.warning(f"Failed to highlight element with XPath '{xpath}': {e}")
            return False

    async def _remove_highlight(self, page: Page, xpath: str) -> None:
        """
        Remove highlight from element.

        Args:
            page: Playwright page object
            xpath: XPath of the element to unhighlight
        """
        try:
            await page.evaluate(
                """
                (xpath) => {
                    const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (element) {
                        element.style.outline = '';
                        element.style.backgroundColor = '';
                        element.removeAttribute('data-highlighted');
                    }
                }
            """,
                xpath,
            )
        except Exception as e:
            logger.warning(f"Failed to remove highlight from element with XPath '{xpath}': {e}")

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory"""
        return self.screenshots_dir
