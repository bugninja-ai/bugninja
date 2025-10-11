"""
Data schemas for Bugninja framework.

This module provides **Pydantic data schemas** for:
- Traversal data structures
- Browser configuration models
- Extended action tracking
- State machine management

## Key Components

1. **Traversal** - Complete test case data structure
2. **BugninjaExtendedAction** - Enhanced action with DOM information
3. **BugninjaBrowserConfig** - Browser configuration settings
4. **ReplayWithHealingStateMachine** - State machine for replay scenarios

## Usage Examples

```python
from bugninja.schemas.pipeline import Traversal, BugninjaExtendedAction

# Create traversal from recorded session
traversal = Traversal(
    test_case="Login flow",
    browser_config=browser_config,
    secrets={"username": "user@example.com"},
    brain_states={},
    actions={}
)

# Create extended action
action = BugninjaExtendedAction(
    brain_state_id="state_123",
    action={"click_element_by_index": {"index": 5}},
    dom_element_data={"xpath": "//button[@id='login']"}
)
```
"""

from .pipeline import (
    BugninjaExtendedAction,
    BugninjaBrowserConfig,
    Traversal,
    BugninjaBrainState,
    ReplayWithHealingStateMachine,
)
from .test_case_io import TestCaseSchema
from .progress import RunProgressState, RunType, RunStatus
from .cli_schemas import TaskInfo, TaskRunConfig, BugninjaTaskResult, TaskExecutionResult

__all__ = [
    "BugninjaExtendedAction",
    "BugninjaBrowserConfig",
    "Traversal",
    "BugninjaBrainState",
    "ReplayWithHealingStateMachine",
    "TestCaseSchema",
    "RunProgressState",
    "RunType",
    "RunStatus",
    "TaskInfo",
    "TaskRunConfig",
    "BugninjaTaskResult",
    "TaskExecutionResult",
]
