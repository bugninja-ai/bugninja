import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from browser_use import BrowserSession  # type: ignore
from browser_use.browser.session import Page  # type: ignore

from src.schemas.pipeline import BugninjaExtendedAction  # type: ignore

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
        action: BugninjaExtendedAction,
        browser_session: Optional[BrowserSession] = None,
    ) -> str:
        """
        Take screenshot and return filename.

        Args:
            page: Playwright page object (used to get context)
            action: Optional action for naming (if None, uses datetime only)
            browser_session: Browser session object for taking screenshots

        Returns:
            Full relative path to screenshot file
        """
        self.screenshot_counter += 1

        if action:
            # Use action type in filename
            action_data = action.model_dump(exclude_unset=True)
            action_type = list(action_data.keys())[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.screenshot_counter:03d}_{action_type}_{timestamp}.png"
        else:
            # Use datetime only
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.png"

        # Take screenshot using browser_session (captures entire browser window)
        if browser_session:
            screenshot_b64 = await browser_session.take_screenshot()

            # Convert base64 to PNG and save
            with open(self.screenshots_dir / filename, "wb") as f:
                f.write(base64.b64decode(screenshot_b64))
        else:
            # Fallback to page screenshot if no browser_session provided
            await page.screenshot(path=str(self.screenshots_dir / filename))

        logger.info(f"📸 Screenshot: {filename}")

        # Return full relative path
        return f"screenshots/{self.screenshots_dir.name}/{filename}"

    async def take_screenshot_with_action_type(
        self,
        page: Page,
        action_type: str,
        browser_session: Optional[BrowserSession] = None,
    ) -> str:
        """
        Take screenshot with action type for naming.

        Args:
            page: Playwright page object
            action_type: String representing the action type for filename
            browser_session: Browser session object for taking screenshots

        Returns:
            Full relative path to screenshot file
        """
        self.screenshot_counter += 1

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

        logger.info(f"📸 Screenshot: {filename}")

        # Return full relative path
        return f"screenshots/{self.screenshots_dir.name}/{filename}"

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory"""
        return self.screenshots_dir

    def get_screenshot_counter(self) -> int:
        """Get the current screenshot counter"""
        return self.screenshot_counter

    def increment_counter(self) -> None:
        """Increment the screenshot counter"""
        self.screenshot_counter += 1
