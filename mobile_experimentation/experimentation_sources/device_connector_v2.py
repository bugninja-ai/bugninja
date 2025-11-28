"""
Device Connector v2 for UI Test Automation
Direct ADB implementation - eliminates abstraction layers for 10x speed improvement
Uses direct ADB shell commands instead of uiautomator2 library
"""

import subprocess
import xml.etree.ElementTree as ET
import time
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class UIElement:
    """Represents a UI element with its properties and selector information"""

    resource_id: Optional[str] = None
    text: Optional[str] = None
    content_desc: Optional[str] = None
    class_name: Optional[str] = None
    bounds: Optional[Tuple[int, int, int, int]] = None
    clickable: bool = False
    enabled: bool = True
    focused: bool = False
    scrollable: bool = False
    checkable: bool = False
    checked: bool = False
    index: Optional[int] = None
    package: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "resource_id": self.resource_id,
            "text": self.text,
            "content_desc": self.content_desc,
            "class_name": self.class_name,
            "bounds": self.bounds,
            "clickable": self.clickable,
            "enabled": self.enabled,
            "focused": self.focused,
            "scrollable": self.scrollable,
            "checkable": self.checkable,
            "checked": self.checked,
            "index": self.index,
            "package": self.package,
        }

    def get_center_coordinates(self) -> Optional[Tuple[int, int]]:
        """Get center coordinates for tapping"""
        if self.bounds:
            x1, y1, x2, y2 = self.bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return (center_x, center_y)
        return None

    def get_selector_options(self) -> List[Dict[str, str]]:
        """Generate possible selector options for this element (compatibility method)"""
        selectors = []

        if self.resource_id:
            selectors.append(
                {
                    "type": "resource_id",
                    "value": self.resource_id,
                    "selector": f'resource_id:{self.resource_id}',
                }
            )

        if self.text:
            selectors.append(
                {
                    "type": "text",
                    "value": self.text,
                    "selector": f'text:{self.text}',
                }
            )

        if self.content_desc:
            selectors.append(
                {
                    "type": "content_desc",
                    "value": self.content_desc,
                    "selector": f'content_desc:{self.content_desc}',
                }
            )

        if self.class_name:
            selectors.append(
                {
                    "type": "class_name",
                    "value": self.class_name,
                    "selector": f'class_name:{self.class_name}',
                }
            )

        return selectors


class DeviceConnectorV2:
    """Direct ADB implementation - 10x faster than uiautomator2"""

    def __init__(
        self, device_serial: Optional[str] = None, device_ip: Optional[str] = None
    ):
        self.device_serial = device_serial
        self.device_ip = device_ip
        self.device_id = None
        self.current_package: Optional[str] = None
        self._device_info: Optional[Dict[str, Any]] = None

    def _run_adb_command(
        self, command: List[str], timeout: int = 10, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run ADB command with device targeting"""
        full_command = ["adb"]

        if self.device_id:
            full_command.extend(["-s", self.device_id])

        full_command.extend(command)

        try:
            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
            )
            return result
        except subprocess.TimeoutExpired:
            console.print(f"✗ ADB command timed out: {' '.join(full_command)}")
            raise
        except Exception as e:
            console.print(f"✗ ADB command failed: {str(e)}")
            raise

    def connect(self) -> bool:
        """Connect to the Android device using direct ADB"""
        try:
            # First check if ADB is available
            try:
                subprocess.run(["adb", "version"], capture_output=True, check=True)
            except subprocess.CalledProcessError:
                console.print(
                    "✗ ADB not found. Please install Android SDK platform-tools"
                )
                return False
            except FileNotFoundError:
                console.print(
                    "✗ ADB not found. Please install Android SDK platform-tools"
                )
                return False

            # Determine device ID
            if self.device_ip:
                # Connect to network device
                connect_result = self._run_adb_command(["connect", self.device_ip])
                if connect_result.returncode != 0:
                    console.print(f"✗ Failed to connect to {self.device_ip}")
                    return False
                self.device_id = self.device_ip
                console.print(f"✓ Connected to device at {self.device_ip}")
            elif self.device_serial:
                self.device_id = self.device_serial
                console.print(f"✓ Using device {self.device_serial}")
            else:
                # Get first available device
                devices_result = self._run_adb_command(["devices"])
                if devices_result.returncode != 0:
                    console.print("✗ Failed to list devices")
                    return False

                lines = devices_result.stdout.strip().split("\n")[1:]  # Skip header
                available_devices = []
                for line in lines:
                    if "\tdevice" in line:
                        device_id = line.split("\t")[0]
                        available_devices.append(device_id)

                if not available_devices:
                    console.print("✗ No devices available")
                    return False

                self.device_id = available_devices[0]
                console.print(f"✓ Connected to default device: {self.device_id}")

            # Test connection and get device info
            info = self._get_device_info()
            if info:
                console.print(
                    f"Device Info: {info.get('product', 'Unknown')} - Android {info.get('version', 'Unknown')}"
                )
                return True
            else:
                console.print("✗ Failed to get device info")
                return False

        except Exception as e:
            console.print(f"✗ Failed to connect to device: {str(e)}")
            return False

    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information using direct ADB"""
        if self._device_info:
            return self._device_info

        info = {}
        try:
            # Get various device properties
            properties = [
                ("product", "ro.product.model"),
                ("version", "ro.build.version.release"),
                ("sdk", "ro.build.version.sdk"),
                ("brand", "ro.product.brand"),
                ("manufacturer", "ro.product.manufacturer"),
            ]

            for key, prop in properties:
                result = self._run_adb_command(["shell", "getprop", prop])
                if result.returncode == 0:
                    value = result.stdout.strip()
                    if value:
                        info[key] = value

            # Get display size
            result = self._run_adb_command(["shell", "wm", "size"])
            if result.returncode == 0:
                size_match = re.search(r"(\d+)x(\d+)", result.stdout)
                if size_match:
                    info["displayWidth"] = int(size_match.group(1))
                    info["displayHeight"] = int(size_match.group(2))

            self._device_info = info
            return info

        except Exception as e:
            console.print(f"Warning: Could not get device info: {str(e)}")
            return {}

    @property
    def info(self) -> Dict[str, Any]:
        """Get device info (compatible with uiautomator2 interface)"""
        device_info = self._get_device_info()
        # Map to uiautomator2 format
        return {
            "productName": device_info.get("product", "Unknown"),
            "model": device_info.get("product", "Unknown"),
            "version": device_info.get("version", "Unknown"),
            "sdkVersion": device_info.get("sdk", "Unknown"),
            "displayWidth": device_info.get("displayWidth", 0),
            "displayHeight": device_info.get("displayHeight", 0),
        }

    def get_current_app_info(self) -> Dict[str, Any]:
        """Get information about the currently focused app"""
        try:
            # Get current activity
            result = self._run_adb_command(
                [
                    "shell",
                    "dumpsys",
                    "window",
                    "windows",
                    "|",
                    "grep",
                    "-E",
                    "mCurrentFocus",
                ]
            )

            if result.returncode == 0:
                # Parse output like: mCurrentFocus=Window{abc123 u0 com.example.app/com.example.MainActivity}
                focus_match = re.search(
                    r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)", result.stdout
                )
                if focus_match:
                    package = focus_match.group(1)
                    activity = focus_match.group(2)
                    self.current_package = package
                    return {
                        "package": package,
                        "activity": activity,
                    }

            # Fallback: try to get top activity
            result = self._run_adb_command(
                ["shell", "dumpsys", "activity", "recents", "|", "grep", "Recent"]
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "Recent #0" in line:
                        package_match = re.search(r"([a-zA-Z0-9_.]+)", line)
                        if package_match:
                            package = package_match.group(1)
                            self.current_package = package
                            return {"package": package, "activity": "Unknown"}

            return {"package": "Unknown", "activity": "Unknown"}

        except Exception as e:
            console.print(
                f"[red]Warning:[/red] Could not get current app info: {str(e)}"
            )
            return {"package": "Unknown", "activity": "Unknown"}

    def take_screenshot(self, filepath: str = "screenshot.png") -> str:
        """Take a screenshot using direct ADB"""
        try:
            # Ensure screenshots are saved in the screenshots folder
            if not filepath.startswith("screenshots/"):
                filename = os.path.basename(filepath)
                filepath = f"screenshots/{filename}"

            # Create screenshots directory if it doesn't exist
            os.makedirs("screenshots", exist_ok=True)

            # Use ADB to take screenshot
            result = self._run_adb_command(
                ["shell", "screencap", "-p", "/sdcard/screenshot.png"]
            )

            if result.returncode != 0:
                raise Exception("Failed to capture screenshot on device")

            # Pull screenshot from device
            pull_result = self._run_adb_command(
                ["pull", "/sdcard/screenshot.png", filepath]
            )

            if pull_result.returncode != 0:
                raise Exception("Failed to pull screenshot from device")

            # Clean up screenshot from device
            self._run_adb_command(["shell", "rm", "/sdcard/screenshot.png"])

            console.print(f"✓ Screenshot saved to {filepath}")
            return filepath

        except Exception as e:
            console.print(f"✗ Failed to take screenshot: {str(e)}")
            raise

    def get_ui_hierarchy(self) -> str:
        """Get the UI hierarchy XML dump using direct ADB"""
        try:
            # Use uiautomator dump command via ADB
            result = self._run_adb_command(
                ["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"]
            )

            if result.returncode != 0:
                raise Exception("Failed to dump UI hierarchy on device")

            # Get the XML content
            cat_result = self._run_adb_command(["shell", "cat", "/sdcard/ui_dump.xml"])

            if cat_result.returncode != 0:
                raise Exception("Failed to read UI dump from device")

            # Clean up dump file from device
            self._run_adb_command(["shell", "rm", "/sdcard/ui_dump.xml"])

            return cat_result.stdout

        except Exception as e:
            console.print(f"✗ Failed to get UI hierarchy: {str(e)}")
            raise

    def extract_ui_elements(self) -> List[UIElement]:
        """Extract all UI elements from the current screen"""
        hierarchy_xml = self.get_ui_hierarchy()
        elements = []

        try:
            root = ET.fromstring(hierarchy_xml)
            for node in root.iter():
                if node.tag == "node":
                    attrs = node.attrib

                    # Parse bounds
                    bounds_str = attrs.get("bounds", "")
                    bounds = None
                    if bounds_str:
                        try:
                            # Parse "[x1,y1][x2,y2]" format
                            coords = (
                                bounds_str.replace("[", "").replace("]", ",").split(",")
                            )
                            if len(coords) >= 4:
                                bounds = (
                                    int(coords[0]),
                                    int(coords[1]),
                                    int(coords[2]),
                                    int(coords[3]),
                                )
                        except (ValueError, IndexError):
                            pass

                    element = UIElement(
                        resource_id=(
                            attrs.get("resource-id")
                            if attrs.get("resource-id")
                            else None
                        ),
                        text=attrs.get("text") if attrs.get("text") else None,
                        content_desc=(
                            attrs.get("content-desc")
                            if attrs.get("content-desc")
                            else None
                        ),
                        class_name=attrs.get("class"),
                        bounds=bounds,
                        clickable=attrs.get("clickable", "false").lower() == "true",
                        enabled=attrs.get("enabled", "true").lower() == "true",
                        focused=attrs.get("focused", "false").lower() == "true",
                        scrollable=attrs.get("scrollable", "false").lower() == "true",
                        checkable=attrs.get("checkable", "false").lower() == "true",
                        checked=attrs.get("checked", "false").lower() == "true",
                        index=(
                            int(attrs.get("index", 0)) if attrs.get("index") else None
                        ),
                        package=attrs.get("package"),
                    )

                    # Only include elements that have some identifying information
                    if any([element.resource_id, element.text, element.content_desc]):
                        elements.append(element)

            console.print(f"Info: Extracted {len(elements)} UI elements")
            return elements

        except ET.ParseError as e:
            console.print(f"✗ Failed to parse UI hierarchy: {str(e)}")
            raise

    def get_interactive_elements(self) -> List[UIElement]:
        """Get only interactive UI elements (clickable, scrollable, etc.)"""
        all_elements = self.extract_ui_elements()
        interactive = [
            element
            for element in all_elements
            if element.clickable or element.scrollable or element.checkable or
            # Include text input fields even if not marked as clickable
            (element.class_name and "EditText" in element.class_name) or
            # Include elements that look like input fields
            (
                element.resource_id
                and any(
                    keyword in element.resource_id.lower()
                    for keyword in ["search", "input", "edit", "text", "field"]
                )
            )
        ]

        console.print(f"Info: Found {len(interactive)} interactive elements")
        return interactive

    def click_element(self, element: UIElement) -> bool:
        """Click on an element using coordinates"""
        coordinates = element.get_center_coordinates()
        if not coordinates:
            console.print("✗ Cannot click element - no coordinates available")
            return False

        x, y = coordinates
        return self.tap_coordinates(x, y)

    def tap_coordinates(self, x: int, y: int) -> bool:
        """Tap at specific coordinates"""
        try:
            result = self._run_adb_command(["shell", "input", "tap", str(x), str(y)])

            if result.returncode == 0:
                console.print(f"✓ Tapped at ({x}, {y})")
                return True
            else:
                console.print(f"✗ Failed to tap at ({x}, {y}): {result.stderr}")
                return False

        except Exception as e:
            console.print(f"✗ Failed to tap: {str(e)}")
            return False

    def input_text(self, text: str) -> bool:
        """Input text using ADB"""
        try:
            # Escape special characters for shell
            escaped_text = text.replace(" ", "%s").replace("'", "\\'")

            result = self._run_adb_command(["shell", "input", "text", escaped_text])

            if result.returncode == 0:
                console.print(f"✓ Input text: '{text}'")
                return True
            else:
                console.print(f"✗ Failed to input text: {result.stderr}")
                return False

        except Exception as e:
            console.print(f"✗ Failed to input text: {str(e)}")
            return False

    def press_key(self, keycode: str) -> bool:
        """Press a key using keycode"""
        try:
            result = self._run_adb_command(["shell", "input", "keyevent", keycode])

            if result.returncode == 0:
                console.print(f"✓ Pressed key: {keycode}")
                return True
            else:
                console.print(f"✗ Failed to press key {keycode}: {result.stderr}")
                return False

        except Exception as e:
            console.print(f"✗ Failed to press key: {str(e)}")
            return False

    def clear_text(self) -> bool:
        """Clear text using select all + delete"""
        try:
            # Select all text (Ctrl+A)
            self.press_key("KEYCODE_CTRL_LEFT")
            time.sleep(0.1)
            self.press_key("KEYCODE_A")
            time.sleep(0.1)
            self.press_key("KEYCODE_CTRL_LEFT")  # Release Ctrl
            time.sleep(0.1)

            # Delete selected text
            self.press_key("KEYCODE_DEL")

            console.print("✓ Cleared text field")
            return True

        except Exception as e:
            console.print(f"✗ Failed to clear text: {str(e)}")
            return False

    def long_click_element(self, element: UIElement) -> bool:
        """Long click on an element"""
        coordinates = element.get_center_coordinates()
        if not coordinates:
            console.print("✗ Cannot long click element - no coordinates available")
            return False

        x, y = coordinates
        try:
            # Use swipe with same start and end coordinates for long press
            result = self._run_adb_command(
                ["shell", "input", "swipe", str(x), str(y), str(x), str(y), "1000"]
            )

            if result.returncode == 0:
                console.print(f"✓ Long clicked at ({x}, {y})")
                return True
            else:
                console.print(f"✗ Failed to long click: {result.stderr}")
                return False

        except Exception as e:
            console.print(f"✗ Failed to long click: {str(e)}")
            return False

    def scroll_element(self, element: UIElement, direction: str = "down") -> bool:
        """Scroll within an element"""
        if not element.bounds:
            console.print("✗ Cannot scroll element - no bounds available")
            return False

        x1, y1, x2, y2 = element.bounds
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        # Calculate scroll distance (1/3 of element height/width)
        scroll_distance = min((x2 - x1), (y2 - y1)) // 3

        try:
            if direction == "down":
                start_y = center_y + scroll_distance // 2
                end_y = center_y - scroll_distance // 2
                result = self._run_adb_command(
                    [
                        "shell",
                        "input",
                        "swipe",
                        str(center_x),
                        str(start_y),
                        str(center_x),
                        str(end_y),
                        "300",
                    ]
                )
            elif direction == "up":
                start_y = center_y - scroll_distance // 2
                end_y = center_y + scroll_distance // 2
                result = self._run_adb_command(
                    [
                        "shell",
                        "input",
                        "swipe",
                        str(center_x),
                        str(start_y),
                        str(center_x),
                        str(end_y),
                        "300",
                    ]
                )
            elif direction == "left":
                start_x = center_x + scroll_distance // 2
                end_x = center_x - scroll_distance // 2
                result = self._run_adb_command(
                    [
                        "shell",
                        "input",
                        "swipe",
                        str(start_x),
                        str(center_y),
                        str(end_x),
                        str(center_y),
                        "300",
                    ]
                )
            elif direction == "right":
                start_x = center_x - scroll_distance // 2
                end_x = center_x + scroll_distance // 2
                result = self._run_adb_command(
                    [
                        "shell",
                        "input",
                        "swipe",
                        str(start_x),
                        str(center_y),
                        str(end_x),
                        str(center_y),
                        "300",
                    ]
                )
            else:
                console.print(f"✗ Unknown scroll direction: {direction}")
                return False

            if result.returncode == 0:
                console.print(f"✓ Scrolled {direction}")
                return True
            else:
                console.print(f"✗ Failed to scroll {direction}: {result.stderr}")
                return False

        except Exception as e:
            console.print(f"✗ Failed to scroll: {str(e)}")
            return False

    def perform_action(
        self, selector_code: str, action: str = "click", **kwargs
    ) -> bool:
        """
        Compatibility method for existing code
        Note: This is a simplified version since we don't use selectors in v2
        Instead, we work directly with elements and coordinates
        """
        console.print(
            f"[yellow]Warning: perform_action with selector '{selector_code}' not supported in v2[/yellow]"
        )
        console.print(
            "[yellow]Use direct element methods instead (click_element, input_text, etc.)[/yellow]"
        )
        return False

    def disconnect(self):
        """Clean up device connection"""
        console.print("Info: Disconnected from device (v2)")


if __name__ == "__main__":
    # Test the device connector v2
    connector = DeviceConnectorV2()
    if connector.connect():
        app_info = connector.get_current_app_info()
        print(f"Current app: {app_info}")

        elements = connector.get_interactive_elements()
        print(f"Found {len(elements)} interactive elements")

        for i, element in enumerate(elements[:5]):  # Show first 5
            print(
                f"{i+1}. {element.text or element.content_desc or element.resource_id}"
            )
            if element.bounds:
                print(f"   Bounds: {element.bounds}")

        connector.disconnect()
