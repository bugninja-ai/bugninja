"""
Event publishers for Bugninja framework.

This module provides various event publishers for tracking and displaying
browser automation operations, run states, and action events.

## Key Components

1. **RichTerminalPublisher** - Rich terminal-based event publisher with colored output

## Usage Examples

```python
from bugninja.events.publishers import RichTerminalPublisher

# Create and use rich terminal publisher
publisher = RichTerminalPublisher()

# Initialize a run
run_id = await publisher.initialize_run("navigation", {"task": "test"})

# Update run state
await publisher.update_run_state(run_id, RunState(current_action="click"))

# Complete the run
await publisher.complete_run(run_id, success=True)
```
"""

from .rich_terminal_publisher import RichTerminalPublisher

__all__ = [
    "RichTerminalPublisher",
]
