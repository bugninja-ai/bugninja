"""
BugNinja V1 - Main Agent Logic
All-in-one prototype for AI web navigation with state logging and replay capability
"""

import asyncio
import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
import patchright.async_api as patchright
from loguru import logger

from config import get_azure_client, Config


class ElementInfo:
    """Simple data class for element information"""

    def __init__(
        self,
        element_id: str,
        selector: str,
        element_type: str,
        text: str,
        bbox: dict,
        is_visible: bool,
        is_enabled: bool,
    ):
        self.id = element_id
        self.selector = selector
        self.type = element_type
        self.text = text
        self.bbox = bbox  # {x, y, width, height}
        self.is_visible = is_visible
        self.is_enabled = is_enabled
        self.coordinates = (
            [bbox["x"] + bbox["width"] // 2, bbox["y"] + bbox["height"] // 2]
            if bbox
            else [0, 0]
        )

    def to_dict(self):
        return {
            "id": self.id,
            "selector": self.selector,
            "type": self.type,
            "text": self.text,
            "bbox": self.bbox,
            "coordinates": self.coordinates,
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
        }


class BugNinjaAgent:
    """Main AI Web Navigation Agent"""

    def __init__(self):
        self.ai_client = get_azure_client()
        self.browser = None
        self.page = None
        self.states = []
        self.current_state_id = None

        # Create directories
        Path(Config.SCREENSHOT_DIR).mkdir(exist_ok=True)
        Path(Config.STATES_DIR).mkdir(exist_ok=True)

        logger.info("BugNinja Agent initialized")

    async def start_browser(self):
        """Initialize Patchright browser with stealth settings"""
        logger.info("Starting browser with stealth configuration...")

        self.playwright = await patchright.async_playwright().start()

        # Use recommended undetectable setup from our design
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            channel=Config.BROWSER_CHANNEL,
            headless=Config.BROWSER_HEADLESS,
            no_viewport=True,
            # No custom headers for maximum stealth
        )

        self.page = await self.browser.new_page()
        logger.success(
            f"Browser started successfully (headless: {Config.BROWSER_HEADLESS})"
        )

    async def extract_elements(self) -> List[ElementInfo]:
        """Extract all interactive elements from the current page"""
        logger.info("Extracting interactive elements...")

        elements = []

        # Define selectors for interactive elements
        selectors = [
            "button",
            "a[href]",
            'input:not([type="hidden"])',
            "select",
            "textarea",
            "[onclick]",
            '[role="button"]',
            '[role="link"]',
            '[tabindex]:not([tabindex="-1"])',
        ]

        for selector in selectors:
            try:
                locators = self.page.locator(selector)
                count = await locators.count()

                for i in range(count):
                    element = locators.nth(i)

                    # Skip if not visible or not in viewport
                    if not await element.is_visible():
                        continue

                    # Extract element information
                    element_id = str(uuid.uuid4())[:8]
                    text = (await element.text_content() or "").strip()[
                        :50
                    ]  # Limit text length
                    bbox = await element.bounding_box()
                    is_enabled = await element.is_enabled()
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")

                    # Skip elements that are too small (likely not meant for interaction)
                    if bbox and (bbox["width"] < 10 or bbox["height"] < 10):
                        continue

                    element_info = ElementInfo(
                        element_id=element_id,
                        selector=selector,
                        element_type=tag_name,
                        text=text,
                        bbox=bbox,
                        is_visible=True,
                        is_enabled=is_enabled,
                    )

                    elements.append(element_info)

            except Exception as e:
                logger.warning(
                    f"Error extracting elements with selector '{selector}': {e}"
                )

        logger.success(f"Extracted {len(elements)} interactive elements")
        return elements

    async def take_annotated_screenshot(
        self, elements: List[ElementInfo], state_id: str
    ) -> str:
        """Take screenshot and annotate with element bounding boxes"""
        logger.info("Taking annotated screenshot...")

        # Take base screenshot
        screenshot_path = os.path.join(Config.SCREENSHOT_DIR, f"state_{state_id}.png")
        await self.page.screenshot(path=screenshot_path, full_page=True)

        # Annotate with bounding boxes
        try:
            image = Image.open(screenshot_path)
            draw = ImageDraw.Draw(image)

            # Try to use a decent font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()

            for i, element in enumerate(elements):
                if not element.bbox:
                    continue

                # Draw bounding box
                bbox = element.bbox
                x1, y1 = bbox["x"], bbox["y"]
                x2, y2 = x1 + bbox["width"], y1 + bbox["height"]

                # Different colors for different element types
                color = {
                    "button": "red",
                    "a": "blue",
                    "input": "green",
                    "select": "orange",
                }.get(element.type, "purple")

                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

                # Draw element number
                draw.text((x1, y1 - 15), f"{i+1}", fill=color, font=font)

            image.save(screenshot_path)
            logger.success(f"Annotated screenshot saved: {screenshot_path}")

        except Exception as e:
            logger.warning(f"Could not annotate screenshot: {e}")

        return screenshot_path

    def format_elements_for_ai(self, elements: List[ElementInfo]) -> str:
        """Format elements list for AI consumption"""
        if not elements:
            return "No interactive elements found on this page."

        formatted = "Available interactive elements:\n"
        for i, element in enumerate(elements[:20]):  # Limit to first 20 elements
            formatted += f"{i+1}. {element.type.upper()}"
            if element.text:
                formatted += f" - '{element.text}'"
            formatted += f" (ID: {element.id})\n"

        if len(elements) > 20:
            formatted += f"... and {len(elements) - 20} more elements\n"

        return formatted

    async def get_ai_decision(
        self, task: str, elements: List[ElementInfo], previous_actions: List[str]
    ) -> Dict[str, Any]:
        """Get AI decision for next action"""
        logger.info("Requesting AI decision...")

        elements_text = self.format_elements_for_ai(elements)
        action_history = (
            "\n".join(previous_actions[-5:])
            if previous_actions
            else "No previous actions"
        )

        prompt = f"""You are an AI web navigation agent. Your task is to navigate a website by choosing atomic actions.

TASK: {task}

CURRENT PAGE ELEMENTS:
{elements_text}

PREVIOUS ACTIONS (last 5):
{action_history}

AVAILABLE ATOMIC ACTIONS:
- click: Click on an element (specify element ID)
- type: Type text (specify text to type)
- scroll: Scroll the page (specify direction: up/down and amount: small/medium/large)
- wait: Wait for page to load or element to appear
- key_press: Press a key (Enter, Tab, Escape, etc.)

Choose the next atomic action that best progresses toward the task goal.

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "action": "click|type|scroll|wait|key_press",
    "target": "element_id_or_text_or_direction",
    "reasoning": "explain why this action makes sense",
    "confidence": 0.95
}}

Choose only ONE action. Be specific and practical."""

        try:
            response = self.ai_client.chat.completions.create(
                model=Config.AZURE_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise web navigation AI that returns valid JSON responses.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=Config.AI_TEMPERATURE,
                max_tokens=500,
            )

            # Parse AI response
            ai_text = response.choices[0].message.content.strip()
            logger.debug(f"AI raw response: {ai_text}")

            # Extract JSON from response
            if "```json" in ai_text:
                ai_text = ai_text.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_text:
                ai_text = ai_text.split("```")[1].split("```")[0].strip()

            decision = json.loads(ai_text)
            logger.success(
                f"AI decision: {decision['action']} - {decision['reasoning']}"
            )
            return decision

        except Exception as e:
            logger.error(f"Error getting AI decision: {e}")
            # Fallback decision
            return {
                "action": "wait",
                "target": "1000",
                "reasoning": "AI decision failed, waiting to recover",
                "confidence": 0.1,
            }

    async def execute_action(
        self, decision: Dict[str, Any], elements: List[ElementInfo]
    ) -> bool:
        """Execute the atomic action decided by AI"""
        action = decision["action"]
        target = decision["target"]

        logger.info(f"Executing action: {action} on {target}")

        try:
            if action == "click":
                # Find element by ID
                element = next((e for e in elements if e.id == target), None)
                if not element:
                    # Try to find by index if target is a number
                    try:
                        index = int(target) - 1
                        if 0 <= index < len(elements):
                            element = elements[index]
                    except ValueError:
                        pass

                if element:
                    locator = self.page.locator(element.selector).first
                    await locator.click()
                    logger.success(f"Clicked element: {element.text or element.type}")
                    return True
                else:
                    logger.error(f"Element not found: {target}")
                    return False

            elif action == "type":
                await self.page.keyboard.type(target)
                logger.success(f"Typed: {target}")
                return True

            elif action == "scroll":
                if "up" in target.lower():
                    await self.page.keyboard.press("PageUp")
                elif "down" in target.lower():
                    await self.page.keyboard.press("PageDown")
                else:
                    await self.page.mouse.wheel(0, 300)  # Default scroll down
                logger.success(f"Scrolled: {target}")
                return True

            elif action == "wait":
                wait_time = int(target) / 1000 if target.isdigit() else 2.0
                await asyncio.sleep(wait_time)
                logger.success(f"Waited: {wait_time}s")
                return True

            elif action == "key_press":
                await self.page.keyboard.press(target)
                logger.success(f"Pressed key: {target}")
                return True

            else:
                logger.error(f"Unknown action: {action}")
                return False

        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return False

    def save_state(
        self,
        elements: List[ElementInfo],
        screenshot_path: str,
        task: str,
        ai_reasoning: str,
        action_taken: Dict[str, Any],
        success: bool,
    ) -> str:
        """Save current state for replay and analysis"""
        state_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        state = {
            "state_id": state_id,
            "timestamp": timestamp,
            "screenshot_path": screenshot_path,
            "url": None,  # Will be filled by caller
            "task_context": task,
            "available_elements": [e.to_dict() for e in elements],
            "ai_reasoning": ai_reasoning,
            "action_taken": action_taken,
            "action_success": success,
            "previous_state_id": self.current_state_id,
        }

        # Save to file
        state_file = os.path.join(Config.STATES_DIR, f"state_{state_id}.json")
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        self.states.append(state)
        self.current_state_id = state_id

        logger.info(f"State saved: {state_id}")
        return state_id

    async def navigate_goal_oriented(self, url: str, task: str, max_steps: int = None):
        """Main goal-oriented navigation function"""
        max_steps = max_steps or Config.MAX_EXPLORATION_STEPS

        logger.info(f"Starting goal-oriented navigation to {url}")
        logger.info(f"Task: {task}")

        await self.start_browser()
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")

        action_history = []

        for step in range(max_steps):
            logger.info(f"=== STEP {step + 1}/{max_steps} ===")

            # Extract elements
            elements = await self.extract_elements()
            if not elements:
                logger.warning("No interactive elements found, stopping")
                break

            # Take screenshot
            screenshot_path = await self.take_annotated_screenshot(
                elements, f"step_{step+1}"
            )

            # Get AI decision
            decision = await self.get_ai_decision(task, elements, action_history)

            # Execute action
            success = await self.execute_action(decision, elements)

            # Save state
            current_url = self.page.url
            state_id = self.save_state(
                elements,
                screenshot_path,
                task,
                decision["reasoning"],
                decision,
                success,
            )

            # Update state with current URL
            self.states[-1]["url"] = current_url

            # Add to action history
            action_summary = (
                f"Step {step+1}: {decision['action']} - {decision['reasoning']}"
            )
            action_history.append(action_summary)

            # Wait a bit for page to settle
            await asyncio.sleep(1)

            # Check if we should continue
            if not success:
                logger.warning("Action failed, but continuing...")

            logger.info(f"Step {step + 1} completed")

        logger.success(f"Navigation completed after {len(action_history)} steps")
        await self.browser.close()

    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()


async def main():
    """Example usage"""
    agent = BugNinjaAgent()

    try:
        # Example: Navigate to a simple form website
        await agent.navigate_goal_oriented(
            url="https://httpbin.org/forms/post",
            task="Fill out the form and submit it",
            max_steps=10,
        )

    except Exception as e:
        logger.error(f"Error in main: {e}")

    finally:
        await agent.close()


if __name__ == "__main__":
    logger.info("Starting BugNinja V1 Prototype")
    asyncio.run(main())
