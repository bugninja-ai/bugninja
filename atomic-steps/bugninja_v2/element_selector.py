"""
Element Selector Module for BugNinja V2

This module handles:
1. Finding all interactable elements on a webpage
2. Executing atomic actions (click, type, hover, scroll)
3. Providing element information for AI decision making
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from patchright.async_api import async_playwright, Page, ElementHandle
import base64
from io import BytesIO


@dataclass
class ElementInfo:
    """Information about an interactable element"""

    id: str  # Unique identifier we assign
    tag_name: str
    text: str
    placeholder: str
    element_type: str  # button, input, link, etc.
    attributes: Dict[str, str]
    bounding_box: Dict[str, float]  # x, y, width, height
    is_visible: bool
    selector: str  # CSS selector to find this element


@dataclass
class ActionResult:
    """Result of executing an atomic action"""

    success: bool
    action: str
    element_id: str
    error_message: Optional[str] = None
    new_url: Optional[str] = None


class ElementSelector:
    """Handles element extraction and atomic actions on web pages"""

    def __init__(self, debug: bool = False):
        self.page: Optional[Page] = None
        self.elements: List[ElementInfo] = []
        self.element_handles: Dict[str, ElementHandle] = {}
        self.debug = debug

    async def initialize(self, page: Page):
        """Initialize with a Playwright page"""
        self.page = page
        await self.refresh_elements()

    async def refresh_elements(self) -> List[ElementInfo]:
        """Extract all interactable elements from the current page"""
        if not self.page:
            raise ValueError("Page not initialized")

        self.elements.clear()
        self.element_handles.clear()

        # Define selectors for different types of interactable elements
        selectors = {
            "button": 'button, input[type="button"], input[type="submit"], input[type="reset"]',
            "link": "a[href]",
            "input": 'input[type="text"], input[type="email"], input[type="password"], input[type="search"], input[type="url"], input[type="tel"], input[type="number"], input:not([type]), input[type=""], input[type="date"], input[type="time"], input[type="datetime-local"], input[type="month"], input[type="week"]',
            "textarea": "textarea, *[role='textbox'], div[contenteditable='true'], div[contenteditable=''], *[contenteditable='true'], *[contenteditable='']",
            "contenteditable": '[contenteditable="true"], [contenteditable=""], [contenteditable]',
            "select": "select",
            "checkbox": 'input[type="checkbox"]',
            "radio": 'input[type="radio"]',
            "clickable": '[onclick], [role="button"], [role="tab"], [role="menuitem"], div[class*="close"], span[class*="close"], *[aria-label*="close"], *[data-dismiss], *[cursor="pointer"]',
        }

        element_id = 0
        if self.debug:
            print(f"\n🔍 ELEMENT DETECTION DEBUG:")
            print(f"Page URL: {self.page.url}")

        for element_type, selector in selectors.items():
            try:
                elements = await self.page.query_selector_all(selector)
                if self.debug:
                    print(
                        f"\n--- {element_type.upper()} ELEMENTS (selector: '{selector}') ---"
                    )
                    print(f"Found {len(elements)} raw elements")

                processed_count = 0
                for element in elements:
                    try:
                        # Check if element is visible
                        is_visible = await element.is_visible()
                        if not is_visible:
                            if self.debug:
                                print(f"  ❌ Skipped: element not visible")
                            continue

                        # Get bounding box
                        bounding_box = await element.bounding_box()
                        if not bounding_box:
                            if self.debug:
                                print(f"  ❌ Skipped: no bounding box")
                            continue

                        # Get element attributes
                        tag_name = await element.evaluate(
                            "el => el.tagName.toLowerCase()"
                        )
                        text = (await element.text_content() or "").strip()
                        placeholder = await element.get_attribute("placeholder") or ""

                        # Get all relevant attributes
                        attributes = {}
                        for attr in [
                            "id",
                            "class",
                            "name",
                            "type",
                            "href",
                            "role",
                            "aria-label",
                            "title",
                        ]:
                            value = await element.get_attribute(attr)
                            if value:
                                attributes[attr] = value

                        # Create unique element ID
                        element_id += 1
                        unique_id = f"elem_{element_id}"

                        # Generate a reliable selector for this element
                        css_selector = await self._generate_selector(element)

                        if self.debug:
                            print(f"  ✅ {unique_id}: {tag_name}")
                            print(
                                f"     Text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
                                if text
                                else "     Text: (empty)"
                            )
                            print(
                                f"     Placeholder: '{placeholder}'"
                                if placeholder
                                else "     Placeholder: (none)"
                            )
                            print(f"     Attributes: {attributes}")
                            print(f"     Generated Selector: '{css_selector}'")
                            print(f"     Position: {bounding_box}")

                        element_info = ElementInfo(
                            id=unique_id,
                            tag_name=tag_name,
                            text=text,
                            placeholder=placeholder,
                            element_type=element_type,
                            attributes=attributes,
                            bounding_box=bounding_box,
                            is_visible=is_visible,
                            selector=css_selector,
                        )

                        self.elements.append(element_info)
                        self.element_handles[unique_id] = element
                        processed_count += 1

                    except Exception as e:
                        if self.debug:
                            print(f"  ❌ Error processing element: {str(e)}")
                        continue

                if self.debug:
                    print(
                        f"Successfully processed {processed_count}/{len(elements)} {element_type} elements"
                    )

            except Exception as e:
                if self.debug:
                    print(f"❌ Error with selector '{selector}': {str(e)}")
                continue

        if self.debug:
            print(f"\n🎯 TOTAL DETECTED: {len(self.elements)} interactive elements")
        return self.elements

    async def _generate_selector(self, element: ElementHandle) -> str:
        """Generate a reliable CSS selector for an element"""
        try:
            # Try to use ID first if available
            element_id = await element.get_attribute("id")
            if element_id:
                return f"#{element_id}"

            # Get basic element info
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            class_name = await element.get_attribute("class")
            name_attr = await element.get_attribute("name")
            placeholder = await element.get_attribute("placeholder")
            text = (await element.text_content() or "").strip()

            # Build selector with multiple fallback strategies
            selectors = []

            # Strategy 1: Use name attribute if available
            if name_attr:
                selectors.append(f'{tag_name}[name="{name_attr}"]')

            # Strategy 2: Use placeholder if unique and short
            if placeholder and len(placeholder) < 100:
                escaped_placeholder = placeholder.replace('"', '\\"')
                selectors.append(f'{tag_name}[placeholder="{escaped_placeholder}"]')

            # Strategy 3: Use class if available
            if class_name:
                # Try with first class
                first_class = class_name.split()[0]
                selectors.append(f"{tag_name}.{first_class}")

                # Try with full class combination (safer)
                safe_classes = [
                    cls
                    for cls in class_name.split()
                    if not any(char in cls for char in [":", "/", "[", "]", "(", ")"])
                ]
                if safe_classes:
                    class_selector = ".".join(safe_classes)
                    selectors.append(f"{tag_name}.{class_selector}")

            # Strategy 4: Use text content if unique and short
            if text and len(text) < 50 and text.count('"') == 0:
                selectors.append(f'{tag_name}:has-text("{text}")')

            # Strategy 5: Use position-based selector (nth-of-type)
            try:
                nth_position = await element.evaluate(
                    """
                    el => {
                        let siblings = Array.from(el.parentNode.children).filter(child => 
                            child.tagName.toLowerCase() === el.tagName.toLowerCase()
                        );
                        return siblings.indexOf(el) + 1;
                    }
                """
                )
                if nth_position > 0:
                    selectors.append(f"{tag_name}:nth-of-type({nth_position})")
            except:
                pass

            # Return the first valid selector, or fallback to tag name
            for selector in selectors:
                if selector:
                    return selector

            return tag_name

        except Exception as e:
            if self.debug:
                print(f"❌ Selector generation error: {str(e)}")
            # Fallback to tag name
            try:
                return await element.evaluate("el => el.tagName.toLowerCase()")
            except:
                return "unknown"

    async def get_element_screenshot(self, element_id: str) -> Optional[str]:
        """Take a screenshot of a specific element and return as base64"""
        if element_id not in self.element_handles:
            return None

        try:
            element = self.element_handles[element_id]
            screenshot_bytes = await element.screenshot()
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception:
            return None

    async def get_page_screenshot_with_annotations(self) -> str:
        """Take a screenshot of the page with bounding boxes around elements"""
        if not self.page:
            raise ValueError("Page not initialized")

        # Take full page screenshot with reduced quality to avoid content filtering
        screenshot_bytes = await self.page.screenshot(
            full_page=True,
            quality=50,  # Reduce quality to make file smaller
            type="jpeg",  # Use JPEG instead of PNG for smaller size
        )

        # For now, return the basic screenshot
        # In a more advanced implementation, we could draw bounding boxes
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    # Atomic Actions

    async def click(self, element_id: str) -> ActionResult:
        """Click on an element"""
        if element_id not in self.element_handles:
            return ActionResult(False, "click", element_id, "Element not found")

        try:
            element = self.element_handles[element_id]

            # Ensure element is still visible and enabled
            if not await element.is_visible():
                return ActionResult(False, "click", element_id, "Element not visible")

            if not await element.is_enabled():
                return ActionResult(False, "click", element_id, "Element not enabled")

            # Scroll into view if needed
            await element.scroll_into_view_if_needed()

            # Try normal click first
            try:
                await element.click(timeout=5000)
            except Exception as normal_click_error:
                # If normal click fails, try force click (useful for modal close buttons)
                try:
                    await element.click(force=True, timeout=5000)
                except Exception as force_click_error:
                    # If both fail, try clicking at coordinates
                    try:
                        box = await element.bounding_box()
                        if box:
                            center_x = box["x"] + box["width"] / 2
                            center_y = box["y"] + box["height"] / 2
                            await self.page.click(
                                f"{center_x},{center_y}", timeout=5000
                            )
                        else:
                            return ActionResult(
                                False,
                                "click",
                                element_id,
                                f"All click methods failed: {str(force_click_error)}",
                            )
                    except Exception as coord_click_error:
                        return ActionResult(
                            False,
                            "click",
                            element_id,
                            f"All click methods failed: normal={str(normal_click_error)}, force={str(force_click_error)}, coords={str(coord_click_error)}",
                        )

            # Wait a moment for any navigation or changes
            await asyncio.sleep(0.5)

            # Check if URL changed
            new_url = self.page.url if self.page else None

            return ActionResult(True, "click", element_id, new_url=new_url)

        except Exception as e:
            return ActionResult(False, "click", element_id, str(e))

    async def type_text(
        self, element_id: str, text: str, clear_first: bool = True
    ) -> ActionResult:
        """Type text into an input element"""
        if self.debug:
            print(f"\n📝 TYPE_TEXT DEBUG for {element_id}:")
            print(f"   Available element handles: {list(self.element_handles.keys())}")
            print(f"   Target element in handles: {element_id in self.element_handles}")

        if element_id not in self.element_handles:
            if self.debug:
                print(f"❌ Element {element_id} not found in handles")
            return ActionResult(False, "type", element_id, "Element not found")

        try:
            element = self.element_handles[element_id]
            if self.debug:
                print(f"✅ Got element handle for {element_id}")

            # Check if element is still valid
            try:
                is_visible = await element.is_visible()
                if self.debug:
                    print(f"   Element visible: {is_visible}")
            except Exception as e:
                if self.debug:
                    print(f"❌ Element handle is stale: {str(e)}")
                return ActionResult(
                    False, "type", element_id, f"Element handle is stale: {str(e)}"
                )

            # Ensure element is visible and enabled
            if not is_visible:
                if self.debug:
                    print(f"❌ Element not visible")
                return ActionResult(False, "type", element_id, "Element not visible")

            is_enabled = await element.is_enabled()
            if self.debug:
                print(f"   Element enabled: {is_enabled}")
            if not is_enabled:
                if self.debug:
                    print(f"❌ Element not enabled")
                return ActionResult(False, "type", element_id, "Element not enabled")

            # Scroll into view if needed
            if self.debug:
                print(f"   Scrolling element into view...")
            await element.scroll_into_view_if_needed()

            # Focus the element
            if self.debug:
                print(f"   Focusing element...")
            await element.focus()
            await asyncio.sleep(0.2)  # Brief wait after focus

            # Get element type to handle different input methods
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            element_type = await element.get_attribute("type")
            is_contenteditable = await element.get_attribute("contenteditable")

            if self.debug:
                print(
                    f"   Tag: {tag_name}, Type: {element_type}, Contenteditable: {is_contenteditable}"
                )

            if is_contenteditable and is_contenteditable.lower() in ["true", ""]:
                if self.debug:
                    print(f"   Using contenteditable approach...")
                # Handle contenteditable elements
                if clear_first:
                    await element.evaluate("el => el.innerHTML = ''")
                await element.type(text, delay=50)  # Slower typing for contenteditable
            elif tag_name in ["input", "textarea"]:
                if self.debug:
                    print(f"   Using standard input/textarea approach...")
                # Handle standard input and textarea elements
                if clear_first:
                    # Try multiple methods to clear the field
                    try:
                        if self.debug:
                            print(f"     Trying fill('')...")
                        await element.fill("")  # Playwright's fill method
                    except Exception as e1:
                        if self.debug:
                            print(f"     Fill failed: {str(e1)}")
                        try:
                            if self.debug:
                                print(f"     Trying direct value setting...")
                            await element.evaluate(
                                "el => el.value = ''"
                            )  # Direct value setting
                        except Exception as e2:
                            if self.debug:
                                print(f"     Direct value setting failed: {str(e2)}")
                            # Fallback: select all and delete
                            if self.debug:
                                print(f"     Trying select all + delete...")
                            await element.press("Control+a")
                            await element.press("Delete")

                # Type the text with a small delay for reliability
                if self.debug:
                    print(f"     Typing text: '{text}'...")
                await element.type(text, delay=25)
            else:
                if self.debug:
                    print(f"   Using fallback approach...")
                # Fallback for other element types
                await element.type(text, delay=50)

            # Verify the text was entered (for debugging)
            try:
                if tag_name in ["input", "textarea"]:
                    current_value = await element.input_value()
                    if self.debug:
                        print(
                            f"   Verification - Expected: '{text}', Got: '{current_value}'"
                        )
                    if current_value != text:
                        return ActionResult(
                            False,
                            "type",
                            element_id,
                            f"Text verification failed. Expected: '{text}', Got: '{current_value}'",
                        )
                elif is_contenteditable:
                    current_text = await element.text_content()
                    if self.debug:
                        print(
                            f"   Verification - Expected: '{text}', Got: '{current_text}'"
                        )
                    if current_text != text:
                        return ActionResult(
                            False,
                            "type",
                            element_id,
                            f"Text verification failed. Expected: '{text}', Got: '{current_text}'",
                        )
            except Exception as e:
                if self.debug:
                    print(f"   ⚠️ Verification failed but continuing: {str(e)}")
                # Verification failed, but typing might have worked
                pass

            if self.debug:
                print(f"✅ Successfully typed text into {element_id}")
            return ActionResult(True, "type", element_id)

        except Exception as e:
            if self.debug:
                print(f"❌ Type operation failed: {str(e)}")
            return ActionResult(False, "type", element_id, f"Typing failed: {str(e)}")

    async def hover(self, element_id: str) -> ActionResult:
        """Hover over an element"""
        if element_id not in self.element_handles:
            return ActionResult(False, "hover", element_id, "Element not found")

        try:
            element = self.element_handles[element_id]

            if not await element.is_visible():
                return ActionResult(False, "hover", element_id, "Element not visible")

            await element.hover()
            await asyncio.sleep(0.3)  # Wait for hover effects

            return ActionResult(True, "hover", element_id)

        except Exception as e:
            return ActionResult(False, "hover", element_id, str(e))

    async def scroll_to(self, element_id: str) -> ActionResult:
        """Scroll to bring an element into view"""
        if element_id not in self.element_handles:
            return ActionResult(False, "scroll", element_id, "Element not found")

        try:
            element = self.element_handles[element_id]
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)

            return ActionResult(True, "scroll", element_id)

        except Exception as e:
            return ActionResult(False, "scroll", element_id, str(e))

    async def select_option(self, element_id: str, option_value: str) -> ActionResult:
        """Select an option from a select element"""
        if element_id not in self.element_handles:
            return ActionResult(False, "select", element_id, "Element not found")

        try:
            element = self.element_handles[element_id]

            if not await element.is_visible():
                return ActionResult(False, "select", element_id, "Element not visible")

            await element.select_option(option_value)

            return ActionResult(True, "select", element_id)

        except Exception as e:
            return ActionResult(False, "select", element_id, str(e))

    def get_elements_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all elements suitable for AI processing"""
        summary = []

        for element in self.elements:
            # Enhanced description for input fields
            description = ""
            if element.element_type in ["input", "textarea", "contenteditable"]:
                if element.placeholder:
                    description = f"Input field: {element.placeholder}"
                elif element.text:
                    description = f"Input field with text: {element.text[:50]}"
                elif element.attributes.get("name"):
                    description = f"Input field (name: {element.attributes['name']})"
                elif element.attributes.get("id"):
                    description = f"Input field (id: {element.attributes['id']})"
                else:
                    input_type = element.attributes.get("type", "text")
                    description = f"Input field (type: {input_type})"
            elif element.element_type == "button":
                if element.text:
                    description = f"Button: {element.text}"
                elif element.attributes.get("value"):
                    description = f"Button: {element.attributes['value']}"
                elif element.attributes.get("aria-label"):
                    description = f"Button: {element.attributes['aria-label']}"
                else:
                    description = "Button"
            elif element.element_type == "link":
                if element.text:
                    description = f"Link: {element.text}"
                elif element.attributes.get("aria-label"):
                    description = f"Link: {element.attributes['aria-label']}"
                else:
                    description = (
                        f"Link to: {element.attributes.get('href', 'unknown')}"
                    )
            else:
                description = (
                    element.text[:50]
                    if element.text
                    else f"{element.element_type} element"
                )

            summary.append(
                {
                    "id": element.id,
                    "type": element.element_type,
                    "tag": element.tag_name,
                    "text": (
                        element.text[:100] if element.text else ""
                    ),  # Truncate long text
                    "placeholder": element.placeholder,
                    "description": description,  # Human-readable description
                    "attributes": element.attributes,
                    "position": {
                        "x": element.bounding_box["x"],
                        "y": element.bounding_box["y"],
                        "width": element.bounding_box["width"],
                        "height": element.bounding_box["height"],
                    },
                }
            )

        return summary

    def debug_elements(self) -> None:
        """Print debug information about all detected elements"""
        print(f"\n=== DETECTED ELEMENTS ({len(self.elements)}) ===")
        for element in self.elements:
            print(f"ID: {element.id}")
            print(f"  Type: {element.element_type}")
            print(f"  Tag: {element.tag_name}")
            print(
                f"  Text: '{element.text[:50]}...' "
                if len(element.text) > 50
                else f"  Text: '{element.text}'"
            )
            print(f"  Placeholder: '{element.placeholder}'")
            print(f"  Attributes: {element.attributes}")
            print(f"  Position: {element.bounding_box}")
            print(f"  Selector: {element.selector}")
            print("---")

    async def re_find_element(self, element_id: str) -> bool:
        """Try to re-find an element if it became stale"""
        if element_id not in self.element_handles:
            if self.debug:
                print(f"❌ Element {element_id} not in element_handles")
            return False

        # Get the element info
        element_info = None
        for elem in self.elements:
            if elem.id == element_id:
                element_info = elem
                break

        if not element_info:
            if self.debug:
                print(f"❌ Element {element_id} not found in elements list")
            return False

        if self.debug:
            print(f"🔄 Trying to re-find element {element_id}")
            print(f"   Original selector: '{element_info.selector}'")
            print(f"   Element type: {element_info.element_type}")
            print(f"   Tag: {element_info.tag_name}")
            print(f"   Attributes: {element_info.attributes}")

        # Strategy 1: Try the original generated selector
        try:
            new_element = await self.page.query_selector(element_info.selector)
            if new_element and await new_element.is_visible():
                if self.debug:
                    print(
                        f"✅ Re-found using original selector: '{element_info.selector}'"
                    )
                self.element_handles[element_id] = new_element
                return True
        except Exception as e:
            if self.debug:
                print(f"❌ Original selector failed: {str(e)}")

        # Strategy 2: Try alternative selectors based on attributes
        alternative_selectors = []

        # Use name attribute
        if element_info.attributes.get("name"):
            alternative_selectors.append(
                f'{element_info.tag_name}[name="{element_info.attributes["name"]}"]'
            )

        # Use placeholder
        if element_info.placeholder:
            escaped_placeholder = element_info.placeholder.replace('"', '\\"')
            alternative_selectors.append(
                f'{element_info.tag_name}[placeholder="{escaped_placeholder}"]'
            )

        # Use ID if available
        if element_info.attributes.get("id"):
            alternative_selectors.append(f'#{element_info.attributes["id"]}')

        # Use class combinations
        if element_info.attributes.get("class"):
            classes = element_info.attributes["class"].split()
            if classes:
                # Try first class
                alternative_selectors.append(f"{element_info.tag_name}.{classes[0]}")
                # Try all classes
                if len(classes) > 1:
                    safe_classes = [
                        cls
                        for cls in classes
                        if not any(
                            char in cls for char in [":", "/", "[", "]", "(", ")"]
                        )
                    ]
                    if safe_classes:
                        class_selector = ".".join(safe_classes)
                        alternative_selectors.append(
                            f"{element_info.tag_name}.{class_selector}"
                        )

        # Try each alternative selector
        for selector in alternative_selectors:
            try:
                if self.debug:
                    print(f"   Trying alternative: '{selector}'")
                new_element = await self.page.query_selector(selector)
                if new_element and await new_element.is_visible():
                    if self.debug:
                        print(f"✅ Re-found using alternative selector: '{selector}'")
                    self.element_handles[element_id] = new_element
                    return True
            except Exception as e:
                if self.debug:
                    print(f"   ❌ Alternative selector '{selector}' failed: {str(e)}")

        # Strategy 3: Try to find by position and tag name
        try:
            tag_elements = await self.page.query_selector_all(element_info.tag_name)
            if self.debug:
                print(
                    f"   Found {len(tag_elements)} {element_info.tag_name} elements on page"
                )

            for i, elem in enumerate(tag_elements):
                if await elem.is_visible():
                    bbox = await elem.bounding_box()
                    if bbox:
                        # Check if position is similar (within 50px tolerance)
                        original_bbox = element_info.bounding_box
                        if (
                            abs(bbox["x"] - original_bbox["x"]) < 50
                            and abs(bbox["y"] - original_bbox["y"]) < 50
                        ):
                            if self.debug:
                                print(
                                    f"✅ Re-found using position matching (element {i+1})"
                                )
                            self.element_handles[element_id] = elem
                            return True
        except Exception as e:
            if self.debug:
                print(f"   ❌ Position-based search failed: {str(e)}")

        if self.debug:
            print(f"❌ Could not re-find element {element_id} using any strategy")
        return False

    async def wait_for_page_load(self, timeout: int = 5000):
        """Wait for page to be reasonably loaded (more practical approach)"""
        if self.page:
            try:
                # Try to wait for load state with a shorter timeout
                await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            except Exception:
                # If that fails, just wait a reasonable amount of time
                await asyncio.sleep(2)
                pass  # Continue anyway, the page might still be usable

    async def debug_textarea_detection(self) -> None:
        """Debug method to specifically check textarea detection"""
        if not self.page:
            return

        print(f"\n🔍 TEXTAREA DEBUG ANALYSIS:")

        # Test different textarea selectors
        textarea_selectors = [
            "textarea",
            "*[role='textbox']",
            "div[contenteditable='true']",
            "*[contenteditable='true']",
            "*[contenteditable='']",
            "*[contenteditable]",
            "textarea, *[role='textbox'], div[contenteditable='true'], *[contenteditable='true'], *[contenteditable='']",
        ]

        for selector in textarea_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                print(f"\nSelector: '{selector}' -> Found {len(elements)} elements")

                for i, element in enumerate(elements):
                    try:
                        is_visible = await element.is_visible()
                        tag_name = await element.evaluate(
                            "el => el.tagName.toLowerCase()"
                        )
                        text = (await element.text_content() or "").strip()
                        placeholder = await element.get_attribute("placeholder") or ""
                        class_attr = await element.get_attribute("class") or ""
                        id_attr = await element.get_attribute("id") or ""

                        print(f"  Element {i+1}:")
                        print(f"    - Tag: {tag_name}")
                        print(f"    - Visible: {is_visible}")
                        print(
                            f"    - Text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
                            if text
                            else "    - Text: (empty)"
                        )
                        print(
                            f"    - Placeholder: '{placeholder}'"
                            if placeholder
                            else "    - Placeholder: (none)"
                        )
                        print(
                            f"    - Class: '{class_attr}'"
                            if class_attr
                            else "    - Class: (none)"
                        )
                        print(
                            f"    - ID: '{id_attr}'" if id_attr else "    - ID: (none)"
                        )

                        if is_visible:
                            bbox = await element.bounding_box()
                            print(f"    - Position: {bbox}")

                    except Exception as e:
                        print(f"    - Error getting info: {str(e)}")

            except Exception as e:
                print(f"Selector '{selector}' failed: {str(e)}")
