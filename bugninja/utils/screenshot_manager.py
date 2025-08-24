import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from browser_use import BrowserSession  # type: ignore
from patchright.async_api import Page  # type: ignore
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from bugninja.schemas.pipeline import BugninjaExtendedAction  # type: ignore

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Unified screenshot management for all agents and replay sessions."""

    def __init__(self, run_id: str, folder_prefix: str = "traversal"):
        """
        Initialize screenshot manager.

        Args:
            folder_prefix: Prefix for screenshot folders (traversal, replay, etc.)
        """
        self.folder_prefix = folder_prefix
        self.run_id = run_id
        self.screenshots_dir = self._get_screenshots_dir()
        self.screenshots_dir.mkdir(exist_ok=True)
        self.screenshot_counter = 0
        logger.info(f"📸 Screenshots will be saved to: {self.screenshots_dir}")

    def _get_screenshots_dir(self) -> Path:
        """Get the screenshots directory for current session"""

        base_dir = Path("./screenshots")
        base_dir.mkdir(exist_ok=True)

        return base_dir / f"{self.run_id}"

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

        # Extract element coordinates without visual highlighting
        coordinates = None
        if action.dom_element_data:
            # Wait for element to be present and visible
            await page.wait_for_timeout(500)
            coordinates = await self._get_element_coordinates(page, action.dom_element_data)

        # Generate filename
        action_data = action.model_dump(exclude_unset=True)
        action_type = list(action_data.keys())[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.screenshot_counter:03d}_{action_type}_{timestamp}.png"

        # Take clean screenshot without any highlighting
        await self._take_clean_screenshot(page, browser_session, filename)

        # Draw rectangle on screenshot if coordinates found
        if coordinates:
            self._draw_rectangle_on_screenshot(self.screenshots_dir / filename, coordinates)

        logger.info(f"📸 Screenshot: {filename}")

        # Return full relative path
        return f"screenshots/{self.screenshots_dir.name}/{filename}"

    async def _get_element_coordinates(
        self, page: Page, dom_element_data: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """
        Extract element coordinates using XPath with enhanced popup detection and debugging.

        Args:
            page: Playwright page object
            dom_element_data: DOM element data containing XPath selectors

        Returns:
            Dictionary with x, y, width, height coordinates, or None if element not found
        """
        # Get main XPath
        main_xpath: Optional[str] = dom_element_data.get("xpath")
        if not main_xpath:
            logger.debug("No main XPath found in dom_element_data")
            return None

        # Enhanced debugging: Log the XPath we're trying
        logger.debug(f"Attempting coordinate extraction for XPath: {main_xpath}")

        # Try main XPath first
        coordinates = await self._get_coordinates_with_xpath(page, main_xpath)
        if coordinates:
            logger.debug(f"Successfully extracted coordinates for main XPath: {coordinates}")
            return coordinates

        # Try alternative XPaths
        alternative_xpaths = dom_element_data.get("alternative_relative_xpaths", [])
        for i, alt_xpath in enumerate(alternative_xpaths):
            logger.debug(f"Trying alternative XPath {i+1}: {alt_xpath}")
            coordinates = await self._get_coordinates_with_xpath(page, alt_xpath)
            if coordinates:
                logger.debug(
                    f"Successfully extracted coordinates for alternative XPath {i+1}: {coordinates}"
                )
                return coordinates

        # NEW: Enhanced popup detection and fallback
        logger.debug("All XPaths failed, attempting popup-specific detection")
        popup_coordinates = await self._try_popup_specific_selectors(page)
        if popup_coordinates:
            logger.debug(
                f"Successfully extracted coordinates using popup detection: {popup_coordinates}"
            )
            return popup_coordinates

        logger.warning("Failed to extract coordinates for any XPath or popup selector")
        return None

    async def _get_coordinates_with_xpath(
        self, page: Page, xpath: str
    ) -> Optional[Dict[str, float]]:
        """
        Extract coordinates using specific XPath with document-relative positioning.

        Args:
            page: Playwright page object
            xpath: XPath selector to find element

        Returns:
            Dictionary with x, y, width, height coordinates, or None if element not found
        """
        try:
            # Wait for element to be present and visible before extracting coordinates
            # This handles timing issues with popups and dynamic content
            try:
                # Use Playwright's locator to wait for element with timeout
                locator = page.locator(f"xpath={xpath}")
                await locator.wait_for(state="visible", timeout=100)  # 0.1 second timeout
            except Exception as wait_error:
                logger.debug(f"Element with XPath '{xpath}' not found within timeout: {wait_error}")
                return None

            # Now extract coordinates since element is confirmed to be visible
            coordinates: Optional[Dict[str, float]] = await page.evaluate(
                """
                (xpath) => {
                    const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (element) {
                        // Check if element is visible and not clipped
                        const style = window.getComputedStyle(element);
                        const isVisible = style.display !== 'none' && 
                                         style.visibility !== 'hidden' && 
                                         style.opacity !== '0' &&
                                         element.offsetWidth > 0 &&
                                         element.offsetHeight > 0;
                        
                        if (isVisible) {
                            const rect = element.getBoundingClientRect();
                            const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
                            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
                            
                            return {
                                x: rect.left + scrollX,
                                y: rect.top + scrollY,
                                width: rect.width,
                                height: rect.height
                            };
                        }
                    }
                    return null;
                }
                """,
                xpath,
            )

            if coordinates and coordinates.get("width", 0) > 0 and coordinates.get("height", 0) > 0:
                return coordinates

            return None

        except Exception as e:
            logger.warning(f"Failed to get coordinates for XPath '{xpath}': {e}")
            return None

    async def _try_popup_specific_selectors(self, page: Page) -> Optional[Dict[str, float]]:
        """
        Try to find popup elements when main XPath fails.

        Args:
            page: Playwright page object

        Returns:
            Coordinates of popup interaction element, or None if not found
        """
        try:

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("load")

            # First, detect if there are any popups present
            popup_elements = await self._detect_popup_elements(page)
            if not popup_elements:
                logger.debug("No popup elements detected")
                return None

            logger.debug(f"Detected {len(popup_elements)} popup elements: {popup_elements}")

            # Try to find common popup interaction elements
            popup_coordinates = await self._find_popup_interaction_element(page, popup_elements)
            if popup_coordinates:
                return popup_coordinates

            # If no specific interaction element found, try to highlight the popup itself
            popup_coordinates = await self._highlight_popup_container(page, popup_elements)
            if popup_coordinates:
                return popup_coordinates

            return None

        except Exception as e:
            logger.warning(f"Error in popup-specific selector detection: {e}")
            return None

    async def _detect_popup_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Detect visible popup/modal elements on the page.

        Args:
            page: Playwright page object

        Returns:
            List of detected popup elements with their properties
        """
        try:
            popup_elements: List[Dict[str, Any]] = await page.evaluate(
                """
                () => {
                    const popups = [];
                    
                    // Look for common popup patterns
                    const selectors = [
                        '[role="dialog"]',
                        '[role="modal"]',
                        '.modal',
                        '.popup',
                        '.dialog',
                        '[data-modal]',
                        '[data-popup]',
                        '.overlay',
                        '[class*="modal"]',
                        '[class*="popup"]',
                        '[class*="dialog"]'
                    ];
                    
                    selectors.forEach(selector => {
                        try {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => {
                                const style = window.getComputedStyle(el);
                                const rect = el.getBoundingClientRect();
                                
                                // Check if element is visible and has reasonable size
                                if (style.display !== 'none' && 
                                    style.visibility !== 'hidden' && 
                                    style.opacity !== '0' &&
                                    rect.width > 0 && 
                                    rect.height > 0) {
                                    
                                    popups.push({
                                        tagName: el.tagName,
                                        className: el.className,
                                        id: el.id,
                                        role: el.getAttribute('role'),
                                        width: rect.width,
                                        height: rect.height,
                                        x: rect.x,
                                        y: rect.y
                                    });
                                }
                            });
                        } catch (e) {
                            // Ignore selector errors
                        }
                    });
                    
                    return popups;
                }
            """
            )

            return popup_elements

        except Exception as e:
            logger.warning(f"Error detecting popup elements: {e}")
            return []

    async def _find_popup_interaction_element(
        self, page: Page, popup_elements: List[Dict[str, Any]]
    ) -> Optional[Dict[str, float]]:
        """
        Find common interaction elements within popups.

        Args:
            page: Playwright page object
            popup_elements: List of detected popup elements

        Returns:
            Coordinates of interaction element, or None if not found
        """
        # Common popup interaction selectors (ordered by priority)
        interaction_selectors = [
            'button[aria-label*="close" i]',
            'button[aria-label*="dismiss" i]',
            ".close",
            ".close-button",
            '[data-dismiss="modal"]',
            'button:contains("Close")',
            'button:contains("Cancel")',
            'button:contains("X")',
            '[class*="close"]',
            'button[type="button"]',  # Generic button fallback
        ]

        # Try to find interaction elements within the detected popups
        for popup in popup_elements:
            popup_selector = self._get_popup_selector(popup)
            if not popup_selector:
                continue

            for interaction_selector in interaction_selectors:
                try:
                    # Search within the specific popup
                    full_selector = f"{popup_selector} {interaction_selector}"
                    logger.debug(f"Trying popup interaction selector: {full_selector}")
                    coordinates = await self._get_coordinates_with_selector(page, full_selector)
                    if coordinates:
                        logger.debug(
                            f"Found popup interaction element with selector '{full_selector}': {coordinates}"
                        )
                        return coordinates
                except Exception as e:
                    logger.debug(f"Selector '{full_selector}' failed: {e}")
                    continue

        # Fallback: try global selectors if popup-specific search fails
        for selector in interaction_selectors:
            try:
                logger.debug(f"Trying global interaction selector: {selector}")
                coordinates = await self._get_coordinates_with_selector(page, selector)
                if coordinates:
                    logger.debug(
                        f"Found global interaction element with selector '{selector}': {coordinates}"
                    )
                    return coordinates
            except Exception as e:
                logger.debug(f"Global selector '{selector}' failed: {e}")
                continue

        return None

    def _get_popup_selector(self, popup: Dict[str, Any]) -> Optional[str]:
        """
        Generate a CSS selector for a detected popup element.

        Args:
            popup: Popup element data

        Returns:
            CSS selector for the popup, or None if cannot be generated
        """
        tag_name: str = popup.get("tagName", "").lower()
        popup_id = popup.get("id")
        popup_class = popup.get("className", "").split()[0] if popup.get("className") else None
        popup_role = popup.get("role")

        # Prefer ID if available
        if popup_id:
            return f"#{popup_id}"

        # Use role if available
        if popup_role:
            return f'[role="{popup_role}"]'

        # Use class if available
        if popup_class:
            return f".{popup_class}"

        # Fallback to tag name
        if tag_name:
            return tag_name

        return None

    async def _highlight_popup_container(
        self, page: Page, popup_elements: List[Dict[str, Any]]
    ) -> Optional[Dict[str, float]]:
        """
        Highlight the popup container itself if no specific interaction element is found.

        Args:
            page: Playwright page object
            popup_elements: List of detected popup elements

        Returns:
            Coordinates of the largest popup container, or None if not found
        """
        if not popup_elements:
            return None

        # Find the largest popup (most likely the main popup)
        largest_popup = max(popup_elements, key=lambda p: p.get("width", 0) * p.get("height", 0))

        # Use the popup's position and size as coordinates
        coordinates = {
            "x": float(largest_popup.get("x", 0)),
            "y": float(largest_popup.get("y", 0)),
            "width": float(largest_popup.get("width", 0)),
            "height": float(largest_popup.get("height", 0)),
        }

        logger.debug(f"Highlighting popup container: {coordinates}")
        return coordinates

    async def _get_coordinates_with_selector(
        self, page: Page, selector: str
    ) -> Optional[Dict[str, float]]:
        """
        Extract coordinates using CSS selector instead of XPath.

        Args:
            page: Playwright page object
            selector: CSS selector to find element

        Returns:
            Dictionary with x, y, width, height coordinates, or None if element not found
        """

        try:
            # Wait for element to be present and visible
            try:
                locator = page.locator(selector)
                await locator.wait_for(state="visible", timeout=100)  # 0.1 second timeout
            except Exception as wait_error:
                logger.debug(
                    f"Element with selector '{selector}' not found within timeout: {wait_error}"
                )
                return None

            # Extract coordinates using CSS selector
            coordinates: Optional[Dict[str, float]] = await page.evaluate(
                """
                (selector) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        // Check if element is visible and not clipped
                        const style = window.getComputedStyle(element);
                        const isVisible = style.display !== 'none' && 
                                         style.visibility !== 'hidden' && 
                                         style.opacity !== '0' &&
                                         element.offsetWidth > 0 &&
                                         element.offsetHeight > 0;
                        
                        if (isVisible) {
                            const rect = element.getBoundingClientRect();
                            const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
                            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
                            
                            return {
                                x: rect.left + scrollX,
                                y: rect.top + scrollY,
                                width: rect.width,
                                height: rect.height
                            };
                        }
                    }
                    return null;
                }
                """,
                selector,
            )

            if coordinates and coordinates.get("width", 0) > 0 and coordinates.get("height", 0) > 0:
                return coordinates

            return None

        except Exception as e:
            logger.warning(f"Failed to get coordinates for selector '{selector}': {e}")
            return None

    async def _take_clean_screenshot(
        self, page: Page, browser_session: Optional[BrowserSession], filename: str
    ) -> None:
        """
        Take clean screenshot with full page capture to include popups and overlays.

        Args:
            page: Playwright page object
            browser_session: Browser session object (not used, kept for compatibility)
            filename: Name of the file to save the screenshot
        """
        # Always use page.screenshot with full_page=True for consistent behavior
        # This ensures popups, modals, and overlays are captured
        await page.screenshot(path=str(self.screenshots_dir / filename), full_page=True)

    def _draw_rectangle_on_screenshot(
        self, screenshot_path: Path, coordinates: Dict[str, float]
    ) -> None:
        """
        Draw red 3px solid rectangle on screenshot using Pillow.

        Args:
            screenshot_path: Path to the screenshot file
            coordinates: Dictionary with x, y, width, height coordinates
        """
        try:
            with Image.open(screenshot_path) as img:
                draw = ImageDraw.Draw(img)

                # Calculate rectangle coordinates
                x1 = float(coordinates["x"])
                y1 = float(coordinates["y"])
                x2 = float(coordinates["x"] + coordinates["width"])
                y2 = float(coordinates["y"] + coordinates["height"])

                # Draw red 3px solid rectangle
                draw.rectangle((x1, y1, x2, y2), outline="red", width=3)

                # Save the modified image
                img.save(screenshot_path)

        except Exception as e:
            logger.warning(f"Failed to draw rectangle on screenshot: {e}")

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory"""
        return self.screenshots_dir
