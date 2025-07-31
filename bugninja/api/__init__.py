"""
Bugninja API - High-level public interface for browser automation.

This module provides a simple, intuitive API for browser automation tasks
with comprehensive type safety and validation using Pydantic models.

## Key Components

1. **BugninjaClient** - Main entry point for browser automation operations
2. **Task** - Pydantic model for defining browser automation tasks
3. **TaskResult** - Pydantic model for task execution results
4. **BugninjaConfig** - Pydantic model for client configuration
5. **Exception Hierarchy** - Comprehensive error handling with specific exception types
"""

from bugninja.api.client import BugninjaClient
from bugninja.api.models import Task, TaskResult, BugninjaConfig
from bugninja.api.exceptions import (
    BugninjaError,
    TaskExecutionError,
    SessionReplayError,
    ConfigurationError,
    LLMError,
)

__version__ = "0.1.0"
__all__ = [
    "BugninjaClient",
    "Task",
    "TaskResult",
    "BugninjaConfig",
    "BugninjaError",
    "TaskExecutionError",
    "SessionReplayError",
    "ConfigurationError",
    "LLMError",
]
