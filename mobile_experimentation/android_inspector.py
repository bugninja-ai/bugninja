#!/usr/bin/env python3
"""Simple Android UI inspector using pure ADB and rich terminal output.

This script:

1. Connects to the first available Android device (or a specific serial if set).
2. Detects the currently focused app (package / activity).
3. Dumps the current UI hierarchy with `uiautomator dump` via ADB.
4. Parses UI elements from the XML (in memory only).
5. Prints all element attributes to the terminal using rich.

No local filesystem writes are performed; only the device-side XML file is used
transiently and removed afterwards.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from rich import print as rich_print
from rich.panel import Panel
from rich.table import Table


@dataclass
class UIElement:
    """Represents a UI element parsed from the uiautomator XML dump.

    Attributes:
        resource_id: Android `resource-id` attribute.
        text: Visible text of the element.
        content_desc: Content description / accessibility label.
        class_name: Fully-qualified widget class name.
        bounds: Tuple of (x1, y1, x2, y2) screen coordinates.
        clickable: Whether the element is clickable.
        enabled: Whether the element is enabled.
        focused: Whether the element currently has focus.
        scrollable: Whether the element can be scrolled.
        checkable: Whether the element can be checked.
        checked: Whether the element is currently checked.
        index: Index within its parent.
        package: Package that owns this view.
    """

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
        """Convert this element to a serializable dict."""
        return asdict(self)

    def short_label(self) -> str:
        """Build a short human-readable label for logging."""
        parts: List[str] = []
        if self.text:
            parts.append(f"text={self.text!r}")
        if self.content_desc:
            parts.append(f"content_desc={self.content_desc!r}")
        if self.resource_id:
            parts.append(f"id={self.resource_id!r}")
        if self.class_name:
            parts.append(f"class={self.class_name.split('.')[-1]!r}")
        if not parts:
            return "<unnamed element>"
        return ", ".join(parts)

    def bounds_str(self) -> str:
        """Return bounds as a compact string representation."""
        if not self.bounds:
            return "-"
        x1, y1, x2, y2 = self.bounds
        return f"[{x1},{y1}][{x2},{y2}]"


class AndroidInspector:
    """Pure-ADB Android UI inspector.

    This class is intentionally self-contained:
    - No project-local imports
    - No env file loading
    - No local filesystem writes

    It just talks to ADB, parses the UI hierarchy, and prints everything
    using rich.
    """

    def __init__(
        self,
        device_serial: Optional[str] = None,
        adb_path: str = "adb",
        command_timeout: int = 10,
    ) -> None:
        """Initialize the inspector.

        Args:
            device_serial: Optional fixed device serial to target.
            adb_path: Name or path of the adb executable.
            command_timeout: Default timeout in seconds for adb commands.
        """
        self.adb_path = adb_path
        self.device_serial = device_serial
        self.device_id: Optional[str] = None
        self.command_timeout = command_timeout

        self.ui_dump_device_path = "/sdcard/ui_dump.xml"

        self.device_info: Optional[Dict[str, Any]] = None
        self.current_package: Optional[str] = None
        self.current_activity: Optional[str] = None

        self.last_ui_xml: Optional[str] = None
        self.last_elements: List[UIElement] = []

    # --------------------------------------------------------------------- #
    # Low-level ADB wrapper
    # --------------------------------------------------------------------- #

    def _run_adb_command(
        self,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run an ADB command and return the CompletedProcess.

        This method always prefixes the command with `adb` and, if a device_id
        is set, with `-s <device_id>`.

        It does NOT raise on non-zero return code; callers must inspect
        `result.returncode`.
        """
        cmd: List[str] = [self.adb_path]
        device = self.device_serial or self.device_id
        if device:
            cmd.extend(["-s", device])
        cmd.extend(args)

        if timeout is None:
            timeout = self.command_timeout

        try:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return result
        except subprocess.TimeoutExpired:
            rich_print(f"[red]✗ ADB command timed out:[/red] {' '.join(cmd)}")
            raise
        except FileNotFoundError:
            rich_print(
                "[red]✗ ADB executable not found. "
                "Make sure Android platform-tools are installed and on PATH.[/red]"
            )
            raise
        except Exception as exc:  # shit happens
            rich_print(f"[red]✗ ADB command failed:[/red] {exc}")
            raise

    # --------------------------------------------------------------------- #
    # Connection & device info
    # --------------------------------------------------------------------- #

    def connect(self) -> bool:
        """Resolve a device and verify that ADB can talk to it."""
        # Check adb is available at all
        version_result = self._run_adb_command(["version"])
        if version_result.returncode != 0:
            rich_print("[red]✗ Failed to run 'adb version'. " "Is ADB installed correctly?[/red]")
            return False

        # If user gave a serial, just trust it
        if self.device_serial:
            self.device_id = self.device_serial
            rich_print(f"[green]✓ Using device serial:[/green] {self.device_serial}")
        else:
            # Otherwise, pick the first `device` from `adb devices`
            devices_result = self._run_adb_command(["devices"])
            if devices_result.returncode != 0:
                rich_print("[red]✗ Failed to list devices via 'adb devices'.[/red]")
                rich_print(devices_result.stderr)
                return False

            lines = devices_result.stdout.strip().splitlines()
            # First line is usually "List of devices attached"
            candidates: List[str] = []
            for line in lines[1:]:
                # Format: <serial>\tdevice
                if "\tdevice" in line:
                    serial = line.split("\t", 1)[0].strip()
                    if serial:
                        candidates.append(serial)

            if not candidates:
                rich_print(
                    "[red]✗ No connected devices found. "
                    "Check USB connection and adb authorization.[/red]"
                )
                return False

            self.device_id = candidates[0]
            rich_print(f"[green]✓ Connected to device:[/green] [bold]{self.device_id}[/bold]")

        # Optionally fetch and print some basic device info
        self.device_info = self.get_device_info()
        if self.device_info:
            info_str = ", ".join(f"{k}={v}" for k, v in self.device_info.items() if v is not None)
            rich_print(
                Panel(
                    info_str or "No device info",
                    title="Device Info",
                    expand=False,
                )
            )

        return True

    def get_device_info(self) -> Dict[str, Any]:
        """Get basic device info via getprop + wm size.

        Returns a small dict; failures are swallowed and logged.
        """
        info: Dict[str, Any] = {}
        try:
            props = {
                "product": "ro.product.model",
                "brand": "ro.product.brand",
                "manufacturer": "ro.product.manufacturer",
                "version": "ro.build.version.release",
                "sdk": "ro.build.version.sdk",
            }
            for key, prop in props.items():
                result = self._run_adb_command(["shell", "getprop", prop])
                if result.returncode == 0:
                    value = result.stdout.strip()
                    if value:
                        info[key] = value

            size_result = self._run_adb_command(["shell", "wm", "size"])
            if size_result.returncode == 0:
                m = re.search(r"(\d+)x(\d+)", size_result.stdout)
                if m:
                    info["displayWidth"] = int(m.group(1))
                    info["displayHeight"] = int(m.group(2))
        except Exception as exc:
            rich_print(
                f"[yellow]Warning: Failed to get device info via getprop/wm size:[/yellow] {exc}"
            )
        return info

    # --------------------------------------------------------------------- #
    # Foreground app info
    # --------------------------------------------------------------------- #

    def get_current_app_info(self) -> Dict[str, str]:
        """Return the currently focused package/activity, if possible."""
        try:
            # Try dumpsys window first
            result = self._run_adb_command(
                ["shell", "dumpsys", "window", "windows", "|", "grep", "mCurrentFocus"]
            )
            package = "Unknown"
            activity = "Unknown"

            if result.returncode == 0 and result.stdout:
                # Example line:
                # mCurrentFocus=Window{abc123 u0 com.example.app/com.example.MainActivity}
                m = re.search(r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)", result.stdout)
                if m:
                    package = m.group(1)
                    activity = m.group(2)

            self.current_package = package
            self.current_activity = activity

            rich_print(
                Panel(
                    f"package: [bold]{package}[/bold]\n" f"activity: [bold]{activity}[/bold]",
                    title="Current Focused App",
                    expand=False,
                )
            )

            return {"package": package, "activity": activity}

        except Exception as exc:
            rich_print(
                f"[yellow]Warning: Could not determine current app via dumpsys:[/yellow] {exc}"
            )
            return {"package": "Unknown", "activity": "Unknown"}

    # --------------------------------------------------------------------- #
    # UI hierarchy dump & parsing
    # --------------------------------------------------------------------- #

    def dump_ui_hierarchy(self) -> Optional[str]:
        """Dump the UI hierarchy using uiautomator and return the raw XML string."""
        rich_print("[cyan]Dumping UI hierarchy via uiautomator...[/cyan]")

        # Trigger uiautomator dump on the device
        dump_result = self._run_adb_command(
            ["shell", "uiautomator", "dump", self.ui_dump_device_path]
        )
        if dump_result.returncode != 0:
            rich_print("[red]✗ Failed to execute 'uiautomator dump' on device.[/red]")
            rich_print(dump_result.stderr)
            return None

        # Read XML back from device
        cat_result = self._run_adb_command(["shell", "cat", self.ui_dump_device_path])
        if cat_result.returncode != 0:
            rich_print("[red]✗ Failed to read UI dump XML from device path.[/red]")
            rich_print(cat_result.stderr)
            return None

        xml_str = cat_result.stdout
        self.last_ui_xml = xml_str

        # Clean up the file on device; if this fails, just warn
        rm_result = self._run_adb_command(["shell", "rm", self.ui_dump_device_path])
        if rm_result.returncode != 0:
            rich_print("[yellow]Warning: Failed to remove UI dump file from device.[/yellow]")

        return xml_str

    def parse_elements_from_xml(self, xml_str: str) -> List[UIElement]:
        """Parse UI elements from a uiautomator XML dump."""
        elements: List[UIElement] = []
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as exc:
            rich_print(f"[red]✗ Failed to parse UI XML:[/red] {exc}")
            return elements

        for node in root.iter():
            if node.tag != "node":
                continue

            attrs = node.attrib

            # Parse bounds: "[x1,y1][x2,y2]"
            bounds: Optional[Tuple[int, int, int, int]] = None
            bounds_str = attrs.get("bounds", "")
            if bounds_str:
                try:
                    coords = bounds_str.replace("[", "").replace("]", ",").split(",")
                    if len(coords) >= 4:
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = int(coords[2])
                        y2 = int(coords[3])
                        bounds = (x1, y1, x2, y2)
                except (ValueError, IndexError):
                    # Bounds parsing can be flaky, just ignore on failure
                    bounds = None

            element = UIElement(
                resource_id=attrs.get("resource-id") or None,
                text=attrs.get("text") or None,
                content_desc=attrs.get("content-desc") or None,
                class_name=attrs.get("class") or None,
                bounds=bounds,
                clickable=(attrs.get("clickable", "false").lower() == "true"),
                enabled=(attrs.get("enabled", "true").lower() == "true"),
                focused=(attrs.get("focused", "false").lower() == "true"),
                scrollable=(attrs.get("scrollable", "false").lower() == "true"),
                checkable=(attrs.get("checkable", "false").lower() == "true"),
                checked=(attrs.get("checked", "false").lower() == "true"),
                index=int(attrs["index"]) if "index" in attrs else None,
                package=attrs.get("package") or None,
            )

            # Ignore elements with absolutely no identifying info
            if not any(
                [
                    element.resource_id,
                    element.text,
                    element.content_desc,
                    element.class_name,
                ]
            ):
                continue

            elements.append(element)

        self.last_elements = elements
        rich_print(f"[green]✓ Parsed {len(elements)} UI elements from XML.[/green]")
        return elements

    # --------------------------------------------------------------------- #
    # Rich printing
    # --------------------------------------------------------------------- #

    def print_elements(self, elements: List[UIElement]) -> None:
        """Print all elements with full attributes using rich."""
        if not elements:
            rich_print("[yellow]No UI elements to display.[/yellow]")
            return

        table = Table(
            title="Android UI Elements (current screen)",
            show_lines=False,
            expand=True,
        )
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("Package", style="magenta")
        table.add_column("Class", style="white")
        table.add_column("Resource ID", style="green")
        table.add_column("Text", style="yellow")
        table.add_column("Content Desc", style="yellow")
        table.add_column("Bounds", style="blue")
        table.add_column("Flags", style="white")

        for idx, el in enumerate(elements, start=1):
            flags: List[str] = []
            if el.clickable:
                flags.append("clickable")
            if el.enabled:
                flags.append("enabled")
            if el.focused:
                flags.append("focused")
            if el.scrollable:
                flags.append("scrollable")
            if el.checkable:
                flags.append("checkable")
            if el.checked:
                flags.append("checked")

            flags_str = ", ".join(flags) if flags else "-"

            table.add_row(
                str(idx),
                el.package or "-",
                el.class_name or "-",
                el.resource_id or "-",
                el.text or "-",
                el.content_desc or "-",
                el.bounds_str(),
                flags_str,
            )

        rich_print(table)

    # --------------------------------------------------------------------- #
    # High-level inspection entrypoint
    # --------------------------------------------------------------------- #

    def inspect_current_screen(self) -> None:
        """End-to-end flow: connect, get app info, dump UI, parse, print."""
        if not self.connect():
            return

        self.get_current_app_info()

        xml_str = self.dump_ui_hierarchy()
        if not xml_str:
            return

        elements = self.parse_elements_from_xml(xml_str)
        rich_print(elements)
        # self.print_elements(elements)


if __name__ == "__main__":
    inspector = AndroidInspector(
        device_serial="34141FDH20046W", adb_path="/home/arathus/platform-tools/adb"
    )
    inspector.inspect_current_screen()
