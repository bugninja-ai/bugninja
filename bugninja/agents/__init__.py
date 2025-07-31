"""
Bugninja Agents - AI-powered browser automation agents

This module provides the core agent classes for browser automation including
navigation, self-healing, and base agent functionality.
"""

from .navigator_agent import NavigatorAgent
from .healer_agent import HealerAgent
from .bugninja_agent_base import BugninjaAgentBase
from .extensions import BugninjaController

__all__ = ["NavigatorAgent", "HealerAgent", "BugninjaAgentBase", "BugninjaController"]
