"""
Tab-aware browser session wrapper for multi-tab support.

This module provides a thin wrapper around BrowserSession that adds tab context
tracking and active page management for robust multi-tab browser automation.
"""

from typing import Any, Sequence

from browser_use import BrowserSession  # type: ignore
from patchright.async_api import BrowserContext as PatchrightBrowserContext
from patchright.async_api import Page

from bugninja.utils.logging_config import logger
from bugninja.utils.tab_context import TabContext


class TabAwareBrowserSession:
    """
    Wrapper around BrowserSession that adds tab context tracking and active page management.

    This class provides centralized tab state management while maintaining compatibility
    with the existing BrowserSession interface.
    """

    def __init__(self, browser_session: BrowserSession):
        """Initialize with an existing browser session.

        Args:
            browser_session: The underlying BrowserSession to wrap
        """
        self.browser_session = browser_session
        self.tabs = TabContext()

    def __getattr__(self, name: str) -> Any:
        """Delegate all unknown attributes to the underlying browser session."""
        # Don't delegate 'tabs' since we have our own TabContext
        if name == "tabs":
            return self.tabs
        return getattr(self.browser_session, name)

    async def get_active_page(self) -> Page:
        """Get the currently active page based on tab context.

        Returns:
            Page: The currently active page

        Raises:
            Exception: If no pages are available or tab_id is invalid
        """
        # Browser must be initialized for tab-aware operations
        if not hasattr(self.browser_session, "browser") or self.browser_session.browser is None:
            raise Exception("Browser not initialized - cannot get active page")

        contexts: Sequence[PatchrightBrowserContext] = self.browser_session.browser.contexts  # type: ignore

        if not len(contexts):
            raise Exception("No browser contexts found")

        current_context: PatchrightBrowserContext = contexts[0]

        if not len(current_context.pages):
            raise Exception("No pages found in current context")

        # Ensure tab_id is within bounds
        if self.tabs.active_tab_id >= len(current_context.pages):
            logger.warning(f"Active tab_id {self.tabs.active_tab_id} out of bounds, using tab 0")
            self.tabs.set_active(0)

        if self.tabs.active_tab_id < 0:
            logger.warning(f"Invalid active tab_id {self.tabs.active_tab_id}, using tab 0")
            self.tabs.set_active(0)

        return current_context.pages[self.tabs.active_tab_id]

    async def switch_to_tab(self, tab_id: int) -> None:
        """Switch to a specific tab and bring it to the front with enhanced error handling.

        Args:
            tab_id: The tab index to switch to

        Raises:
            Exception: If tab_id is invalid or switching fails
        """
        # Validate tab state before switching
        if not self.validate_tab_state():
            raise Exception("Invalid tab state - cannot switch tabs")

        contexts: Sequence[PatchrightBrowserContext] = self.browser_session.browser.contexts  # type: ignore
        current_context: PatchrightBrowserContext = contexts[0]

        # Enhanced validation with better error messages
        if tab_id >= len(current_context.pages):
            available_tabs = len(current_context.pages)
            raise Exception(
                f"Tab ID {tab_id} out of range - only {available_tabs} tab(s) available (IDs: 0-{available_tabs-1})"
            )

        if tab_id < 0:
            raise Exception(f"Tab ID must be non-negative, got {tab_id}")

        # Log current state for debugging
        logger.bugninja_log(f"🔄 Switching from tab {self.tabs.active_tab_id} to tab {tab_id}")

        try:
            # Update tab context (this will notify listeners)
            self.tabs.set_active(tab_id)

            # Bring the new active page to front
            active_page = await self.get_active_page()
            await active_page.bring_to_front()

            # Force immediate video rebind if video manager is available
            if (
                hasattr(self, "_video_manager")
                and self._video_manager
                and self._video_manager.is_recording
            ):
                try:
                    await self._video_manager.bind_to_page(
                        active_page, self.browser_session.browser_context
                    )
                    logger.bugninja_log("🎥 Video recording rebound to new tab")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to rebind video recording: {e}")

            # Validate switch was successful
            if self.tabs.active_tab_id != tab_id:
                logger.warning(
                    f"⚠️ Tab switch may have failed - expected {tab_id}, got {self.tabs.active_tab_id}"
                )

            logger.bugninja_log(f"✅ Successfully switched to tab {tab_id}")

        except Exception as e:
            # Reset to previous tab if switch failed
            logger.error(f"❌ Failed to switch to tab {tab_id}: {e}")
            raise

    async def get_current_page(self) -> Page:
        """Legacy compatibility method - delegates to get_active_page."""
        return await self.get_active_page()

    def set_video_manager(self, video_manager: Any) -> None:
        """Set video recording manager for automatic rebind on tab switches.

        Args:
            video_manager: Video recording manager instance
        """
        self._video_manager = video_manager

    def validate_tab_state(self) -> bool:
        """Validate current tab state and return True if consistent.

        Returns:
            bool: True if tab state is valid, False otherwise
        """
        try:
            if not hasattr(self.browser_session, "browser") or self.browser_session.browser is None:
                logger.warning("⚠️ Browser not initialized for tab validation")
                return False

            contexts = self.browser_session.browser.contexts
            if not contexts:
                logger.warning("⚠️ No browser contexts found during validation")
                return False

            current_context = contexts[0]
            if not current_context.pages:
                logger.warning("⚠️ No pages found in context during validation")
                return False

            if self.tabs.active_tab_id >= len(current_context.pages) or self.tabs.active_tab_id < 0:
                logger.warning(
                    f"⚠️ Invalid active_tab_id {self.tabs.active_tab_id} for {len(current_context.pages)} pages"
                )
                return False

            return True
        except Exception as e:
            logger.warning(f"⚠️ Tab state validation failed: {e}")
            return False

    def get_tab_count(self) -> int:
        """Get the number of available tabs.

        Returns:
            int: Number of tabs, or 0 if browser not initialized
        """
        try:
            if not hasattr(self.browser_session, "browser") or self.browser_session.browser is None:
                return 0

            contexts = self.browser_session.browser.contexts
            if not contexts:
                return 0

            return len(contexts[0].pages)
        except Exception:
            return 0
