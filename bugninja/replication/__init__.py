"""
Session replication and replay for Bugninja framework.

This module provides **session replay capabilities** with:
- Traversal replay from recorded sessions
- Self-healing mechanisms for failed replays
- Interactive replay with user pauses
- Parallel session replay support

## Key Components

1. **ReplicatorRun** - Main session replay orchestrator
2. **ReplicatorNavigator** - Base class for navigation during replay
3. **HealerAgent** integration - Self-healing during replay failures

## Usage Examples

```python
from bugninja.replication import ReplicatorRun

# Create replicator for session replay
replicator = ReplicatorRun(
    json_path="./traversals/session.json",
    enable_healing=True,
    pause_after_each_step=False
)

# Execute replay
await replicator.start()
```
"""

from .replicator_run import ReplicatorRun
from .replicator_navigation import ReplicatorNavigator, ReplicatorError

__all__ = [
    "ReplicatorRun",
    "ReplicatorNavigator",
    "ReplicatorError",
]
