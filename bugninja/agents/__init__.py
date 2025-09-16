"""
Bugninja Agents - AI-powered browser automation agents

This module provides the **core agent classes** for browser automation including
navigation, self-healing, and base agent functionality.

## Available Agents

1. **NavigatorAgent** - Primary browser automation agent for task execution
2. **HealerAgent** - Self-healing agent for intervention and recovery
3. **BugninjaAgentBase** - Base class with common agent functionality
4. **BugninjaController** - Extended controller with additional actions
"""

from .navigator_agent import NavigatorAgent
from .healer_agent import HealerAgent
from .bugninja_agent_base import BugninjaAgentBase
from .extensions import BugninjaController

__all__ = ["NavigatorAgent", "HealerAgent", "BugninjaAgentBase", "BugninjaController"]
