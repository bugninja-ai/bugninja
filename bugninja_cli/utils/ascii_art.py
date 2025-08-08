"""
ASCII art and visual elements for Bugninja CLI.

This module provides minimalist ASCII art and visual elements
for the CLI interface.
"""

from typing import Optional

import click

from ..themes.colors import BugninjaColors


def get_banner(version: str = "0.1.0") -> str:
    """Get the minimalist Bugninja banner.

    Args:
        version: Version string to display

    Returns:
        Formatted banner string
    """
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║  🥷  BUGNINJA  🥷                                          ║
║                                                              ║
║  AI-Powered Browser Automation Framework                     ║
║  Version: {version}                                             ║
╚══════════════════════════════════════════════════════════════╝
"""
    return banner


def display_banner(version: str = "0.1.0") -> None:
    """Display the Bugninja banner with styling.

    Args:
        version: Version string to display
    """
    banner = get_banner(version)
    styled_banner = BugninjaColors.primary(banner)
    click.echo(styled_banner)


def get_progress_bar(current: int, total: int, width: int = 40) -> str:
    """Generate a progress bar.

    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar

    Returns:
        Progress bar string
    """
    if total == 0:
        return "[" + " " * width + "] 0%"

    percentage = min(100, int((current / total) * 100))
    filled_width = int((current / total) * width)

    bar = "█" * filled_width + "░" * (width - filled_width)
    return f"[{bar}] {percentage}%"


def get_spinner_frames() -> list[str]:
    """Get spinner animation frames.

    Returns:
        List of spinner frame strings
    """
    return ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def get_status_icon(status: str) -> str:
    """Get status icon for different states.

    Args:
        status: Status string (success, error, warning, info, etc.)

    Returns:
        Status icon string
    """
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "running": "🔄",
        "waiting": "⏳",
        "healing": "🩹",
        "browser": "🌐",
        "task": "📋",
        "session": "📁",
        "config": "⚙️",
        "doctor": "🏥",
    }
    return icons.get(status, "•")


def get_operation_icon(operation: str) -> str:
    """Get operation-specific icon.

    Args:
        operation: Operation type (run, replay, parallel, etc.)

    Returns:
        Operation icon string
    """
    icons = {
        "run": "🚀",
        "replay": "🔄",
        "parallel": "⚡",
        "list": "📋",
        "status": "📊",
        "config": "⚙️",
        "doctor": "🏥",
    }
    return icons.get(operation, "•")


def display_separator(char: str = "─", length: int = 60) -> None:
    """Display a separator line.

    Args:
        char: Character to use for separator
        length: Length of separator line
    """
    separator = char * length
    styled_separator = BugninjaColors.muted(separator)
    click.echo(styled_separator)


def display_section_header(title: str, icon: Optional[str] = None) -> None:
    """Display a section header with styling.

    Args:
        title: Section title
        icon: Optional icon to display
    """
    if icon:
        header = f"{icon} {title}"
    else:
        header = title

    styled_header = BugninjaColors.primary(header, bold=True)
    click.echo(f"\n{styled_header}")
    display_separator("─", len(header) + 2)
