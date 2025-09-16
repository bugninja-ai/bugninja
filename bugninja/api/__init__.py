"""
Bugninja API - High-level public interface for browser automation.

This module provides a **simple, intuitive API** for browser automation tasks
with comprehensive type safety and validation using Pydantic models.

## Key Components

1. **BugninjaClient** - Main entry point for browser automation operations
2. **BugninjaTask** - Pydantic model for defining browser automation tasks
3. **BugninjaTaskResult** - Pydantic model for task execution results
4. **BulkBugninjaTaskResult** - Pydantic model for parallel task execution results
5. **BugninjaConfig** - Pydantic model for client configuration
6. **Exception Hierarchy** - Comprehensive error handling with specific exception types

## Usage Examples

```python
from bugninja.api import BugninjaClient, BugninjaTask

# Create client and execute task
client = BugninjaClient()
task = BugninjaTask(description="Navigate to example.com and click login")
result = await client.run_task(task)

# Replay recorded session
session_file = Path("./traversals/session.json")
result = await client.replay_session(session_file, enable_healing=True)
```
"""

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import (
    BugninjaTask,
    BugninjaTaskResult,
    BulkBugninjaTaskResult,
    BugninjaTaskError,
    BugninjaErrorType,
    OperationType,
    HealingStatus,
    BugninjaConfig,
    SessionInfo,
)
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
    "BugninjaTask",
    "BugninjaTaskResult",
    "BulkBugninjaTaskResult",
    "BugninjaTaskError",
    "BugninjaErrorType",
    "OperationType",
    "HealingStatus",
    "BugninjaConfig",
    "SessionInfo",
    "BugninjaError",
    "TaskExecutionError",
    "SessionReplayError",
    "ConfigurationError",
    "LLMError",
]
