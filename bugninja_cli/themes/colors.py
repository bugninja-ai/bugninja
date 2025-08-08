"""
Color theme system for Bugninja CLI.

This module provides consistent color theming using the specified
color palette and semantic color mapping.
"""

import click


class BugninjaColors:
    """Color theme for Bugninja CLI with consistent branding."""

    # Brand colors (using Click-compatible colors)
    PRIMARY = "magenta"  # Main brand color
    ACCENT = "cyan"  # Accent color
    LIGHT = "white"  # Light background

    # Semantic colors
    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    MUTED = "white"

    @classmethod
    def style(cls, text: str, color: str = "primary", bold: bool = False, dim: bool = False) -> str:
        """Apply consistent styling to text.

        Args:
            text: Text to style
            color: Color name or hex value
            bold: Whether to make text bold
            dim: Whether to dim the text

        Returns:
            Styled text string
        """
        color_map = {
            "primary": cls.PRIMARY,
            "accent": cls.ACCENT,
            "light": cls.LIGHT,
            "success": cls.SUCCESS,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "info": cls.INFO,
            "muted": cls.MUTED,
        }

        # Get the actual color value
        actual_color = color_map.get(color, color)

        # Apply styling
        styled = click.style(text, fg=actual_color, bold=bold, dim=dim)
        return styled

    @classmethod
    def success(cls, text: str, bold: bool = False) -> str:
        """Style text as success message."""
        return cls.style(text, "success", bold=bold)

    @classmethod
    def error(cls, text: str, bold: bool = False) -> str:
        """Style text as error message."""
        return cls.style(text, "error", bold=bold)

    @classmethod
    def warning(cls, text: str, bold: bool = False) -> str:
        """Style text as warning message."""
        return cls.style(text, "warning", bold=bold)

    @classmethod
    def info(cls, text: str, bold: bool = False) -> str:
        """Style text as info message."""
        return cls.style(text, "info", bold=bold)

    @classmethod
    def primary(cls, text: str, bold: bool = False) -> str:
        """Style text with primary brand color."""
        return cls.style(text, "primary", bold=bold)

    @classmethod
    def accent(cls, text: str, bold: bool = False) -> str:
        """Style text with accent color."""
        return cls.style(text, "accent", bold=bold)

    @classmethod
    def muted(cls, text: str, bold: bool = False) -> str:
        """Style text as muted/disabled."""
        return cls.style(text, "muted", bold=bold, dim=True)


def echo_success(text: str, bold: bool = False) -> None:
    """Echo success message with styling."""
    click.echo(BugninjaColors.success(text, bold))


def echo_error(text: str, bold: bool = False) -> None:
    """Echo error message with styling."""
    click.echo(BugninjaColors.error(text, bold))


def echo_warning(text: str, bold: bool = False) -> None:
    """Echo warning message with styling."""
    click.echo(BugninjaColors.warning(text, bold))


def echo_info(text: str, bold: bool = False) -> None:
    """Echo info message with styling."""
    click.echo(BugninjaColors.info(text, bold))


def echo_primary(text: str, bold: bool = False) -> None:
    """Echo text with primary brand color."""
    click.echo(BugninjaColors.primary(text, bold))


def echo_accent(text: str, bold: bool = False) -> None:
    """Echo text with accent color."""
    click.echo(BugninjaColors.accent(text, bold))
