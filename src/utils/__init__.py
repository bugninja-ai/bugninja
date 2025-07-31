"""
Bugninja Utils - Utility classes and helpers

This module provides utility classes for screenshot management, selector generation,
and other helper functionality for browser automation.
"""

from .screenshot_manager import ScreenshotManager
from .selector_factory import SelectorFactory

__all__ = ["ScreenshotManager", "SelectorFactory"]
