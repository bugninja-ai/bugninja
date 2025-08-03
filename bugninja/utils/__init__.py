"""
Utility modules for Bugninja framework.

This module provides various utility functions and classes for:
- Screenshot management
- DOM element selection
- And other common utilities
"""

from .screenshot_manager import ScreenshotManager
from .selector_factory import SelectorFactory

__all__ = ["ScreenshotManager", "SelectorFactory"]
