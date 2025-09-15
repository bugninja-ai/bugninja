"""
Screenshot management utilities for Bugninja framework.

This module provides comprehensive screenshot capture and management functionality
for browser automation sessions, including element highlighting, coordinate extraction,
and organized file storage with automatic naming and timestamping.

## Key Components

1. **ScreenshotManager** - Main class for screenshot capture and management
2. **Element Highlighting** - Automatic highlighting of target elements
3. **Coordinate Extraction** - XPath-based element coordinate detection
4. **File Organization** - Automatic folder structure and naming

## Usage Examples

```python
from bugninja.utils import ScreenshotManager

# Create screenshot manager
screenshot_manager = ScreenshotManager(run_id="test_run")

# Take screenshot with element highlighting
filename = await screenshot_manager.take_screenshot(
    page, action, browser_session
)
```

"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from browser_use import BrowserSession  # type: ignore
from patchright.async_api import Page  # type: ignore
from PIL import Image, ImageDraw

from bugninja.utils.logging_config import logger

if TYPE_CHECKING:
    from bugninja.schemas.pipeline import BugninjaExtendedAction


class ScreenshotManager:
    """
    Optimized screenshot capture functionality with element highlighting and organized file storage.

    This class provides comprehensive screenshot capture functionality including
    element highlighting, coordinate extraction, and organized file storage.
    It automatically creates folder structures, generates descriptive filenames,
    and handles element highlighting for better debugging and analysis.

    Attributes:
        folder_prefix (str): Prefix for screenshot folders
        run_id (str): Unique identifier for the current run
        screenshots_dir (Path): Directory where screenshots are stored
        screenshot_counter (int): Counter for sequential screenshot naming

    Example:
        ```python
        from bugninja.utils import ScreenshotManager

        # Create screenshot manager
        screenshot_manager = ScreenshotManager(run_id="test_run")

        # Take screenshot with element highlighting
        filename = await screenshot_manager.take_screenshot(
            page, action, browser_session
        )
        ```
    """

    def __init__(self, run_id: str, base_dir: Optional[Path] = None):
        """Initialize screenshot manager.

        Args:
            run_id (str): Unique identifier for the current run
            base_dir (Optional[Path]): Base directory for screenshots (if None, uses default)
        """
        self.run_id = run_id
        self.screenshots_dir = self._get_screenshots_dir(base_dir)

        self.screenshot_counter = 0
        logger.bugninja_log(f"📸 Screenshots will be saved to: {self.screenshots_dir}")

    def _get_screenshots_dir(self, base_dir: Optional[Path] = None) -> Path:
        """Get the screenshots directory for current session.

        Returns:
            Path: Path to the screenshots directory for the current run
        """
        if base_dir:
            base_dir = base_dir / "screenshots"
        else:
            base_dir = Path("./screenshots")

        base_dir.mkdir(exist_ok=True)
        return base_dir / f"{self.run_id}"

    def _should_extract_coordinates(self, action: "BugninjaExtendedAction") -> bool:
        """Determine if coordinates should be extracted for this action.

        Args:
            action: The action to check

        Returns:
            bool: True if coordinates should be extracted, False otherwise
        """

        # Only extract coordinates for interactive actions
        interactive_actions = [
            "click_element_by_index",
            "input_text",
            "get_dropdown_options",
            "select_dropdown_option",
            "drag_drop",
        ]
        return action.get_action_type() in interactive_actions

    def _generate_filename(self, action: "BugninjaExtendedAction") -> str:
        """Generate filename for screenshot.

        Args:
            action: The action being captured

        Returns:
            str: Generated filename
        """
        self.screenshot_counter += 1
        action_type = action.get_action_type()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.screenshot_counter:03d}_{action_type}_{timestamp}.png"

    async def take_screenshot(
        self,
        page: Page,
        action: "BugninjaExtendedAction",
        browser_session: Optional[BrowserSession] = None,
    ) -> str:
        """Take screenshot with element highlighting and return filename.

        Args:
            page (Page): Playwright page object (used to get context)
            action (BugninjaExtendedAction): Extended action containing DOM element data
            browser_session (Optional[BrowserSession]): Browser session object for taking screenshots

        Returns:
            str: Full relative path to screenshot file

        Example:
            ```python
            filename = await screenshot_manager.take_screenshot(
                page, action, browser_session
            )
            print(f"Screenshot saved: {filename}")
            ```
        """
        # 1. Check if we need coordinates
        coordinates = None
        should_extract = self._should_extract_coordinates(action)

        logger.debug(
            f"Screenshot for action: should_extract={should_extract}, has_dom_data={action.dom_element_data is not None}"
        )

        if should_extract and action.dom_element_data:
            coordinates = await self._get_element_coordinates(page, action.dom_element_data)
            logger.debug(f"⚔️ Coordinates extracted: {coordinates}")

        # 2. Take screenshot
        filename = self._generate_filename(action)
        await self._take_clean_screenshot(page, browser_session, filename)

        # 3. Draw rectangle if coordinates were found
        if coordinates:
            logger.debug(f"#️⃣ Drawing rectangle on screenshot: {filename}")
            self._draw_rectangle_on_screenshot(self.screenshots_dir / filename, coordinates)
        else:
            logger.debug(f"🆘 No coordinates found for screenshot: {filename}")

        screenshot_directory = str(self._get_screenshots_dir() / filename)

        # Return relative path from the traversal directory
        # Screenshots are always in screenshots/{run_id}/ relative to the base directory
        return screenshot_directory

    async def _get_element_coordinates(
        self, page: Page, dom_element_data: Dict[str, Any]
    ) -> Optional[Dict[str, float]]:
        """
        Extract element coordinates using XPath with simplified logic.

        Args:
            page: Playwright page object
            dom_element_data: DOM element data containing XPath selectors

        Returns:
            Dictionary with x, y, width, height coordinates, or None if element not found
        """
        logger.debug(f"Extracting coordinates from dom_element_data: {dom_element_data}")

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
        logger.debug(f"Trying {len(alternative_xpaths)} alternative XPaths")
        for i, alt_xpath in enumerate(alternative_xpaths):
            logger.debug(f"Trying alternative XPath {i+1}: {alt_xpath}")
            coordinates = await self._get_coordinates_with_xpath(page, alt_xpath)
            if coordinates:
                logger.debug(
                    f"Successfully extracted coordinates for alternative XPath {i+1}: {coordinates}"
                )
                return coordinates

        logger.warning("Failed to extract coordinates for any XPath")
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
                await locator.wait_for(state="visible", timeout=50)  # 0.05 second timeout
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

    async def _take_clean_screenshot(
        self, page: Page, browser_session: Optional[BrowserSession], filename: str
    ) -> None:
        """
        Take clean screenshot with optimized settings and timeout configuration.

        Args:
            page: Playwright page object
            browser_session: Browser session object (not used, kept for compatibility)
            filename: Name of the file to save the screenshot
        """
        try:
            # Fast screenshot with font loading bypass
            await page.screenshot(
                path=str(self.screenshots_dir / filename),
                full_page=False,
                timeout=5000,  # 5 second timeout
                animations="disabled",
                caret="hide",
            )
        except Exception as e:
            # Fallback to slower but more reliable method
            logger.warning(f"Fast screenshot failed, trying fallback: {e}")
            await page.screenshot(
                path=str(self.screenshots_dir / filename),
                full_page=False,
                timeout=15000,  # 15 second timeout for fallback
            )

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
            logger.debug(f"Drawing rectangle on {screenshot_path} with coordinates: {coordinates}")

            # Validate coordinates
            if not all(key in coordinates for key in ["x", "y", "width", "height"]):
                logger.warning(f"Invalid coordinates missing required keys: {coordinates}")
                return

            if coordinates["width"] <= 0 or coordinates["height"] <= 0:
                logger.warning(
                    f"Invalid coordinates with zero or negative dimensions: {coordinates}"
                )
                return

            with Image.open(screenshot_path) as img:
                draw = ImageDraw.Draw(img)

                # Calculate rectangle coordinates
                x1 = float(coordinates["x"])
                y1 = float(coordinates["y"])
                x2 = float(coordinates["x"] + coordinates["width"])
                y2 = float(coordinates["y"] + coordinates["height"])

                # Ensure coordinates are within image bounds
                img_width, img_height = img.size
                x1 = max(0, min(x1, img_width))
                y1 = max(0, min(y1, img_height))
                x2 = max(0, min(x2, img_width))
                y2 = max(0, min(y2, img_height))

                logger.debug(
                    f"Drawing rectangle from ({x1}, {y1}) to ({x2}, {y2}) on image {img_width}x{img_height}"
                )

                # Draw red 3px solid rectangle
                draw.rectangle((x1, y1, x2, y2), outline="red", width=3)

                # Save the modified image
                img.save(screenshot_path)
                logger.debug(f"Successfully drew rectangle on screenshot: {screenshot_path}")

        except Exception as e:
            logger.warning(f"Failed to draw rectangle on screenshot {screenshot_path}: {e}")
            import traceback

            logger.debug(f"Rectangle drawing error traceback: {traceback.format_exc()}")

    def get_screenshots_dir(self) -> Path:
        """Get the current screenshots directory"""
        return self.screenshots_dir
