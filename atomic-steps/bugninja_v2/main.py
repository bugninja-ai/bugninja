"""
BugNinja V2 - Main Navigation Agent

This is the main script that orchestrates the web navigation agent.
It combines element selection, AI decision making, and browser automation.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
from datetime import datetime
import base64

# Import Patchright for stealth browsing
from patchright.async_api import async_playwright

# Import our custom modules
from element_selector import ElementSelector, ElementInfo, ActionResult
from ai_client import AIClient, AIDecision, NavigationContext

# For beautiful logging
from loguru import logger

# For creating movies from screenshots
import cv2
import numpy as np
from PIL import Image
import io


@dataclass
class NavigationState:
    """Represents the current state of navigation"""

    url: str
    page_title: str
    step_number: int
    timestamp: datetime
    elements_count: int
    screenshot_path: Optional[str] = None
    action_taken: Optional[Dict[str, Any]] = None
    ai_decision: Optional[Dict[str, Any]] = None


class BugNinja:
    """Main navigation agent class"""

    def __init__(
        self, headless: bool = False, max_steps: int = 30, debug_elements: bool = False
    ):
        self.headless = headless
        self.max_steps = max_steps
        self.debug_elements = debug_elements

        # Components
        self.element_selector = ElementSelector(debug=self.debug_elements)
        self.ai_client = AIClient(debug=self.debug_elements)

        # Navigation state
        self.current_goal: str = ""
        self.navigation_history: List[NavigationState] = []
        self.previous_actions: List[Dict[str, Any]] = []

        # Tab management
        self.initial_tab_count = 0
        self.last_known_url = ""

        # Recording management
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recording_dir = (
            Path(__file__).parent / "recording" / self.session_timestamp
        )
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_paths: List[str] = []

        # Target resolution for consistency
        self.target_width = 1280
        self.target_height = 720

        # Browser components
        self.browser = None
        self.page = None
        self.playwright = None

        # Configure logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure beautiful logging with loguru"""
        # Remove default logger
        logger.remove()

        # Add console logger with colors (simplified format)
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="INFO",
            colorize=True,
        )

        # Add file logger (with more details for debugging) - now in recording folder
        log_file = self.recording_dir / "bugninja.log"
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
        )

    async def initialize(self) -> bool:
        """Initialize the browser and components"""
        try:
            logger.info("🚀 Initializing BugNinja V2...")

            # Start Playwright
            self.playwright = await async_playwright().start()

            # Launch browser with stealth settings
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            # Create new page with user agent
            self.page = await self.browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Set viewport to target resolution
            await self.page.set_viewport_size(
                {"width": self.target_width, "height": self.target_height}
            )

            # Initialize tab tracking
            self.initial_tab_count = len(self.browser.contexts[0].pages)
            logger.debug(f"🔢 Initial tab count: {self.initial_tab_count}")
            logger.debug(
                f"📋 Initial pages: {[page.url for page in self.browser.contexts[0].pages]}"
            )

            # Initialize element selector
            await self.element_selector.initialize(self.page)

            logger.success("✅ BugNinja initialized successfully!")
            logger.info(f"📁 Recording to: {self.recording_dir}")

            # Log AI client info
            ai_info = self.ai_client.get_client_info()
            logger.info(f"🤖 AI Client: {ai_info['model']} ({ai_info['status']})")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize BugNinja: {str(e)}")
            return False

    async def navigate_to_goal(self, url: str, goal: str) -> bool:
        """
        Navigate to a URL and achieve the specified goal

        Args:
            url: Starting URL
            goal: What we want to achieve

        Returns:
            True if goal was achieved, False otherwise
        """

        self.current_goal = goal
        logger.info(f"🎯 Goal: {goal}")
        logger.info(f"🌐 Starting URL: {url}")

        try:
            # Navigate to the starting URL with more practical loading detection
            logger.info("🚀 Navigating to target URL...")

            try:
                # Try with domcontentloaded first (faster, more reliable)
                await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                logger.info("✅ Page DOM loaded")
            except Exception as e:
                logger.warning(
                    f"⚠️ DOM loading timeout, trying basic navigation: {str(e)}"
                )
                try:
                    # Fallback: just navigate without waiting
                    await self.page.goto(url, timeout=10000)
                    logger.info("✅ Basic navigation completed")
                except Exception as e2:
                    logger.error(f"❌ Navigation completely failed: {str(e2)}")
                    return False

            # Wait a reasonable time for the page to render
            await asyncio.sleep(3)

            # Check if we actually got to a page
            current_url = self.page.url
            if not current_url or current_url == "about:blank":
                logger.error("❌ Navigation failed - no valid page loaded")
                return False

            # Initialize URL tracking for tab management
            self.last_known_url = current_url

            logger.success(f"✅ Successfully navigated to: {current_url}")

            # Start the navigation loop
            return await self._navigation_loop()

        except Exception as e:
            logger.error(f"❌ Navigation failed: {str(e)}")
            return False

    async def _navigation_loop(self) -> bool:
        """Main navigation loop following refined step logic"""

        for step in range(1, self.max_steps + 1):
            # Add spacing between steps for better readability
            if step > 1:
                logger.info("")
                logger.info("")

            logger.info(f"📍 Step {step}/{self.max_steps}")

            try:
                # 1. Wait for page load (with timeout protection)
                try:
                    await self.element_selector.wait_for_page_load(timeout=3000)
                except Exception:
                    logger.debug("⏱️ Page load wait timed out, continuing anyway")
                    pass

                await asyncio.sleep(1)  # Brief settling time

                # Record current state
                current_url = self.page.url
                page_title = await self.page.title()

                logger.info(f"🔗 Current URL: {current_url}")
                logger.info(f"📄 Page Title: {page_title}")

                # 2. Refresh elements on the page
                await self.element_selector.refresh_elements()
                elements_summary = self.element_selector.get_elements_summary()

                logger.info(f"🔍 Found {len(elements_summary)} interactive elements")

                # Debug: Show all detected elements if debug mode is enabled
                if self.debug_elements:
                    self.element_selector.debug_elements()
                    # Also run specific textarea debugging
                    await self.element_selector.debug_textarea_detection()

                # 3. Create screenshot BEFORE making decision
                screenshot_path = await self._save_screenshot(step, "before_action")

                # Take screenshot for AI context (base64)
                screenshot_b64 = (
                    await self.element_selector.get_page_screenshot_with_annotations()
                )

                # Build navigation context
                context = NavigationContext(
                    current_url=current_url,
                    page_title=page_title,
                    goal=self.current_goal,
                    previous_actions=self.previous_actions[-5:],  # Last 5 actions
                    step_number=step,
                )

                # 4. & 5. Check if goal is achieved AND select action from elements (same AI call)
                logger.info(
                    "🤖 Asking AI to analyze screenshot and decide next action..."
                )
                ai_decision = await self.ai_client.decide_next_action(
                    elements_summary=elements_summary,
                    context=context,
                    page_screenshot=screenshot_b64,  # Re-enable with safety improvements
                )

                logger.info(f"🎯 Goal Achieved: {ai_decision.is_goal_complete}")
                logger.info(f"💭 AI Decision: {ai_decision.action_type}")
                logger.info(f"📝 Reasoning: {ai_decision.reasoning}")
                logger.info(f"🎯 Confidence: {ai_decision.confidence:.2f}")
                if ai_decision.recommended_next_step:
                    logger.info(
                        f"👉 Next Step Recommendation: {ai_decision.recommended_next_step}"
                    )

                # 4.1. If goal is achieved, return success
                if (
                    ai_decision.is_goal_complete
                    or ai_decision.action_type == "complete"
                ):
                    logger.success("🎉 Goal achieved!")
                    # Take final screenshot
                    final_screenshot = await self._save_screenshot(
                        step, "goal_achieved"
                    )
                    self._record_state(
                        current_url,
                        page_title,
                        step,
                        len(elements_summary),
                        screenshot_path=final_screenshot,
                        ai_decision=asdict(ai_decision),
                    )
                    return True

                # 6. Save screenshot with the action highlighted (if element selected)
                action_info = f"{ai_decision.action_type}"
                if ai_decision.element_id:
                    action_info += f"_{ai_decision.element_id}"

                # 7. Perform action
                action_result = await self._execute_action(ai_decision)

                # For actions that commonly open new tabs (like clicking links),
                # check for new tabs immediately with a brief wait
                if (
                    action_result
                    and action_result.success
                    and ai_decision.action_type == "click"
                    and ai_decision.element_id
                ):

                    # Find the clicked element to see if it was a link
                    clicked_element = None
                    for elem in elements_summary:
                        if elem["id"] == ai_decision.element_id:
                            clicked_element = elem
                            break

                    if clicked_element and (
                        clicked_element["type"] == "link"
                        or "href" in clicked_element.get("attributes", {})
                    ):
                        logger.debug(
                            "🔗 Clicked a link - checking for new tabs immediately..."
                        )
                        # Give a moment for the new tab to appear
                        await asyncio.sleep(0.3)

                # Check for new tabs or navigation changes after action
                logger.debug("🔍 Checking for tab changes...")
                tab_changed = await self._check_and_switch_tabs()

                if tab_changed:
                    # Give new page time to load completely
                    await asyncio.sleep(2)

                    # Refresh elements on the new page
                    await self.element_selector.refresh_elements()
                    logger.info("🔄 Refreshed elements after tab switch")
                else:
                    logger.debug("📍 No tab switch occurred")

                # 8. Save step to logs
                self._record_state(
                    current_url,
                    page_title,
                    step,
                    len(elements_summary),
                    screenshot_path=screenshot_path,  # Use the before-action screenshot
                    action_taken=asdict(action_result) if action_result else None,
                    ai_decision=asdict(ai_decision),
                )

                # Record action for context
                action_context = {
                    "step": step,
                    "action": ai_decision.action_type,
                    "element_id": ai_decision.element_id,
                    "reasoning": ai_decision.reasoning[:200],  # Truncate for context
                    "result": action_result.success if action_result else False,
                    "error": (
                        action_result.error_message
                        if action_result and not action_result.success
                        else None
                    ),
                    "tab_changed": tab_changed,
                    "recommended_next_step": ai_decision.recommended_next_step,
                }
                self.previous_actions.append(action_context)

                # Wait a bit before next action
                await asyncio.sleep(1)

                # Check if we need to wait for page changes
                if ai_decision.action_type == "wait":
                    logger.info("⏳ Waiting for page changes...")
                    await asyncio.sleep(3)
                    continue

                # If action failed, continue to next step
                if action_result and not action_result.success:
                    logger.warning(f"⚠️ Action failed: {action_result.error_message}")
                    continue

                # Wait for any page transitions after successful action (but don't be too strict)
                if (
                    action_result
                    and action_result.success
                    and ai_decision.action_type in ["click", "type", "select"]
                ):
                    if not tab_changed:  # Only wait if we didn't already switch tabs
                        logger.debug("⏳ Waiting for potential page changes...")
                        await asyncio.sleep(
                            2
                        )  # Let page changes settle, but don't wait too long

            except Exception as e:
                logger.error(f"❌ Error in step {step}: {str(e)}")
                # Save error screenshot
                await self._save_screenshot(step, f"error_{str(e)[:20]}")
                continue

        # 9. Stop gracefully if maximum steps is achieved
        logger.warning(
            f"⏰ Maximum steps ({self.max_steps}) reached without achieving goal"
        )
        return False

    async def _execute_action(self, decision: AIDecision) -> Optional[ActionResult]:
        """Execute the AI's decision"""

        # Log the AI's element choice with detailed info
        if decision.element_id:
            logger.info(f"🎯 AI chose element: {decision.element_id}")

            # Find the element info
            element_info = None
            for elem in self.element_selector.elements:
                if elem.id == decision.element_id:
                    element_info = elem
                    break

            if element_info:
                logger.info(f"   📝 Element Details:")
                logger.info(f"     - Type: {element_info.element_type}")
                logger.info(f"     - Tag: {element_info.tag_name}")
                logger.info(
                    f"     - Text: '{element_info.text[:100]}{'...' if len(element_info.text) > 100 else ''}'"
                )
                logger.info(f"     - Placeholder: '{element_info.placeholder}'")
                logger.info(f"     - Attributes: {element_info.attributes}")
                logger.info(f"     - Generated Selector: '{element_info.selector}'")
                logger.info(f"     - Position: {element_info.bounding_box}")
            else:
                logger.error(
                    f"   ❌ Element {decision.element_id} not found in detected elements!"
                )
                # Show what elements ARE available
                logger.info(f"   📋 Available elements:")
                for elem in self.element_selector.elements:
                    logger.info(
                        f"     - {elem.id}: {elem.element_type} ({elem.tag_name}) - '{elem.text[:30]}{'...' if len(elem.text) > 30 else ''}'"
                    )
        else:
            logger.warning(
                f"⚠️  AI provided no element ID for action: {decision.action_type}"
            )

        try:
            if decision.action_type == "click":
                logger.info(f"👆 Clicking element {decision.element_id}")
                result = await self.element_selector.click(decision.element_id)

                # If element not found, try to re-find it
                if not result.success and "Element not found" in result.error_message:
                    logger.debug(f"🔄 Trying to re-find element {decision.element_id}")
                    if await self.element_selector.re_find_element(decision.element_id):
                        logger.debug("✅ Element re-found, retrying click")
                        result = await self.element_selector.click(decision.element_id)

                return result

            elif decision.action_type == "type":
                logger.info(
                    f"⌨️ Typing '{decision.text_input}' into element {decision.element_id}"
                )
                result = await self.element_selector.type_text(
                    decision.element_id, decision.text_input
                )

                # If element not found, try to re-find it
                if not result.success and "Element not found" in result.error_message:
                    logger.debug(f"🔄 Trying to re-find element {decision.element_id}")
                    if await self.element_selector.re_find_element(decision.element_id):
                        logger.debug("✅ Element re-found, retrying type")
                        result = await self.element_selector.type_text(
                            decision.element_id, decision.text_input
                        )

                return result

            elif decision.action_type == "hover":
                logger.info(f"🖱️ Hovering over element {decision.element_id}")
                result = await self.element_selector.hover(decision.element_id)

                # If element not found, try to re-find it
                if not result.success and "Element not found" in result.error_message:
                    logger.debug(f"🔄 Trying to re-find element {decision.element_id}")
                    if await self.element_selector.re_find_element(decision.element_id):
                        logger.debug("✅ Element re-found, retrying hover")
                        result = await self.element_selector.hover(decision.element_id)

                return result

            elif decision.action_type == "scroll":
                logger.info(f"📜 Scrolling to element {decision.element_id}")
                result = await self.element_selector.scroll_to(decision.element_id)

                # If element not found, try to re-find it
                if not result.success and "Element not found" in result.error_message:
                    logger.debug(f"🔄 Trying to re-find element {decision.element_id}")
                    if await self.element_selector.re_find_element(decision.element_id):
                        logger.debug("✅ Element re-found, retrying scroll")
                        result = await self.element_selector.scroll_to(
                            decision.element_id
                        )

                return result

            elif decision.action_type == "select":
                logger.info(
                    f"📋 Selecting '{decision.option_value}' in element {decision.element_id}"
                )
                result = await self.element_selector.select_option(
                    decision.element_id, decision.option_value
                )

                # If element not found, try to re-find it
                if not result.success and "Element not found" in result.error_message:
                    logger.debug(f"🔄 Trying to re-find element {decision.element_id}")
                    if await self.element_selector.re_find_element(decision.element_id):
                        logger.debug("✅ Element re-found, retrying select")
                        result = await self.element_selector.select_option(
                            decision.element_id, decision.option_value
                        )

                return result

            elif decision.action_type == "wait":
                logger.info("⏳ AI decided to wait")
                return ActionResult(True, "wait", "", None)

            elif decision.action_type == "complete":
                logger.success("✅ AI marked goal as complete")
                return ActionResult(True, "complete", "", None)

            else:
                logger.error(f"❌ Unknown action type: {decision.action_type}")
                return ActionResult(
                    False, decision.action_type, "", "Unknown action type"
                )

        except Exception as e:
            logger.error(
                f"❌ Failed to execute action {decision.action_type}: {str(e)}"
            )
            return ActionResult(
                False, decision.action_type, decision.element_id or "", str(e)
            )

    def _record_state(
        self,
        url: str,
        title: str,
        step: int,
        elements_count: int,
        screenshot_path: Optional[str] = None,
        action_taken: Optional[Dict] = None,
        ai_decision: Optional[Dict] = None,
    ):
        """Record the current navigation state"""
        state = NavigationState(
            url=url,
            page_title=title,
            step_number=step,
            timestamp=datetime.now(),
            elements_count=elements_count,
            screenshot_path=screenshot_path,
            action_taken=action_taken,
            ai_decision=ai_decision,
        )
        self.navigation_history.append(state)

    def save_session_log(self) -> str:
        """Save the complete navigation session to a JSON file"""
        log_file = self.recording_dir / "session.json"

        session_data = {
            "goal": self.current_goal,
            "total_steps": len(self.navigation_history),
            "success": len(self.navigation_history) > 0
            and self.navigation_history[-1].ai_decision
            and self.navigation_history[-1].ai_decision.get("is_goal_complete", False),
            "navigation_history": [asdict(state) for state in self.navigation_history],
            "ai_client_info": self.ai_client.get_client_info(),
            "session_timestamp": self.session_timestamp,
            "target_resolution": f"{self.target_width}x{self.target_height}",
        }

        with open(log_file, "w") as f:
            json.dump(session_data, f, indent=2, default=str)

        logger.info(f"📁 Session log saved to: {log_file}")
        return str(log_file)

    async def _save_screenshot(self, step_number: int, action_info: str = "") -> str:
        """Save a screenshot for the current step, ensuring 1280x720 resolution"""
        try:
            filename = f"step_{step_number:03d}_{action_info}.png"
            screenshot_path = self.recording_dir / filename

            # Take screenshot with exact viewport size (not full page)
            screenshot_bytes = await self.page.screenshot(full_page=False)

            # Load image and ensure it's exactly 1280x720
            image = Image.open(io.BytesIO(screenshot_bytes))

            # Resize/crop to target resolution if needed
            if image.size != (self.target_width, self.target_height):
                # If image is larger, crop from center
                if image.width > self.target_width or image.height > self.target_height:
                    left = max(0, (image.width - self.target_width) // 2)
                    top = max(0, (image.height - self.target_height) // 2)
                    right = left + self.target_width
                    bottom = top + self.target_height
                    image = image.crop((left, top, right, bottom))

                # If image is smaller, resize to target
                image = image.resize(
                    (self.target_width, self.target_height), Image.Resampling.LANCZOS
                )

            # Save the processed image
            image.save(screenshot_path, "PNG")

            self.screenshot_paths.append(str(screenshot_path))
            logger.info(
                f"📸 Screenshot saved: {filename} ({self.target_width}x{self.target_height})"
            )

            return str(screenshot_path)

        except Exception as e:
            logger.error(f"❌ Failed to save screenshot: {str(e)}")
            return ""

    def _create_navigation_movie(self) -> str:
        """Create a movie from all saved screenshots with consistent 1280x720 resolution"""
        try:
            if not self.screenshot_paths:
                logger.warning("⚠️ No screenshots to create movie")
                return ""

            movie_path = self.recording_dir / "navigation_movie.mp4"

            logger.info(
                f"🎬 Creating navigation movie from {len(self.screenshot_paths)} screenshots..."
            )

            # Define the codec and create VideoWriter object with target resolution
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = 0.5  # Each screenshot shows for 2 seconds (1/0.5 = 2)
            video = cv2.VideoWriter(
                str(movie_path), fourcc, fps, (self.target_width, self.target_height)
            )

            # Add each screenshot to the video
            for i, screenshot_path in enumerate(self.screenshot_paths):
                img = cv2.imread(screenshot_path)
                if img is not None:
                    # Ensure image is exactly the target resolution
                    current_height, current_width = img.shape[:2]

                    if (current_width, current_height) != (
                        self.target_width,
                        self.target_height,
                    ):
                        # Resize to target resolution
                        img = cv2.resize(img, (self.target_width, self.target_height))

                    video.write(img)
                    logger.debug(
                        f"Added screenshot {i+1}/{len(self.screenshot_paths)} to movie"
                    )
                else:
                    logger.warning(f"⚠️ Could not read screenshot: {screenshot_path}")

            # Release everything
            video.release()
            cv2.destroyAllWindows()

            logger.success(f"🎬 Navigation movie created: {movie_path}")
            return str(movie_path)

        except Exception as e:
            logger.error(f"❌ Failed to create navigation movie: {str(e)}")
            return ""

    async def cleanup(self):
        """Clean up browser resources and create movie"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        # Create navigation movie
        movie_path = self._create_navigation_movie()
        if movie_path:
            logger.info(f"🎬 Navigation movie saved to: {movie_path}")

        logger.info("🧹 Cleanup completed")
        logger.info(f"📁 All files saved in: {self.recording_dir}")

    async def _check_and_switch_tabs(self) -> bool:
        """Check for new tabs and switch to the most relevant one"""
        try:
            # Try multiple times with small delays to catch new tabs immediately
            max_retries = 3
            for attempt in range(max_retries):
                current_pages = self.browser.contexts[0].pages
                current_tab_count = len(current_pages)

                logger.debug(
                    f"🔍 Tab check attempt {attempt + 1}/{max_retries} - Current: {current_tab_count}, Initial: {self.initial_tab_count}"
                )

                # If new tabs appeared, switch to the newest one
                if current_tab_count > self.initial_tab_count:
                    logger.info(
                        f"🔄 New tab detected! Tab count: {self.initial_tab_count} → {current_tab_count}"
                    )

                    # Get the newest page (last in the list)
                    newest_page = current_pages[-1]

                    # Set viewport size for the new tab to maintain consistency
                    await newest_page.set_viewport_size(
                        {"width": self.target_width, "height": self.target_height}
                    )
                    logger.debug(
                        f"🖥️ Set new tab viewport to {self.target_width}x{self.target_height}"
                    )

                    # Wait for the new page to load
                    try:
                        await newest_page.wait_for_load_state(
                            "domcontentloaded", timeout=5000
                        )
                        logger.debug("✅ New tab loaded")
                    except Exception as e:
                        logger.debug(f"⚠️ New tab load timeout: {str(e)}")
                        pass

                    # Switch to the newest page
                    old_url = self.page.url if self.page else "unknown"
                    self.page = newest_page
                    await self.element_selector.initialize(self.page)

                    new_url = self.page.url
                    logger.success(f"✅ Switched to new tab: {old_url} → {new_url}")

                    # Update tab count
                    self.initial_tab_count = current_tab_count
                    self.last_known_url = new_url

                    return True

                # If no new tab yet, wait a bit and try again (except on last attempt)
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Wait 500ms before next check

            # After all attempts, check if URL changed significantly (navigation within same tab)
            current_url = self.page.url
            if current_url != self.last_known_url:
                logger.info(f"🔄 Page navigated: {self.last_known_url} → {current_url}")
                self.last_known_url = current_url
                return True

            logger.debug(f"🔍 No tab changes detected after {max_retries} attempts")
            return False

        except Exception as e:
            logger.error(f"❌ Error checking tabs: {str(e)}")
            import traceback

            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return False

    async def _close_unnecessary_tabs(self):
        """Close tabs that are not the current active tab (optional cleanup)"""
        try:
            current_pages = self.browser.contexts[0].pages

            # Keep only the current active page and close others
            for page in current_pages:
                if page != self.page:
                    try:
                        await page.close()
                        logger.debug("🗑️ Closed inactive tab")
                    except:
                        pass

        except Exception as e:
            logger.debug(f"Tab cleanup warning: {str(e)}")


async def main():
    """Main entry point"""

    # Example usage
    debug_mode = "--debug" in sys.argv
    bug_ninja = BugNinja(headless=False, max_steps=15, debug_elements=debug_mode)

    try:
        # Initialize
        if not await bug_ninja.initialize():
            logger.error("Failed to initialize BugNinja")
            return

        # Example goal - modify these for your needs
        url = "https://bacprep.ro"
        goal = "Log in using imetstamas@gmail.com and lolxd123 and then complete a section 3 Type test with a proper input and then evaulauate it to see the scores"

        # You can also get these from command line arguments
        if len(sys.argv) >= 3:
            # Filter out the --debug flag when parsing URLs and goals
            args = [arg for arg in sys.argv[1:] if arg != "--debug"]
            if len(args) >= 2:
                url = args[0]
                goal = args[1]

        if debug_mode:
            logger.info(
                "🐛 Debug mode enabled - will show detailed element information"
            )

        # Navigate and achieve goal
        success = await bug_ninja.navigate_to_goal(url, goal)

        # Save session log
        log_file = bug_ninja.save_session_log()

        if success:
            logger.success("🎉 Mission accomplished!")
        else:
            logger.warning("⚠️ Goal not achieved within maximum steps")

    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
    finally:
        # Always cleanup
        await bug_ninja.cleanup()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
