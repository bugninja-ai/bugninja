"""
Bugninja Schemas - Data models and structures

This module provides Pydantic models and data structures for browser automation
including traversal data, browser configurations, and action representations.
"""

from .pipeline import (
    Traversal,
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
)

__all__ = [
    "Traversal",
    "BugninjaBrowserConfig",
    "BugninjaExtendedAction",
]
