"""
Event system for Bugninja framework.

This module provides a **comprehensive event system** for tracking and monitoring
browser automation operations with:
- Event publishing and subscription
- Run state tracking and management
- Multiple publisher types (null, rich terminal, etc.)
- Event manager for centralized event handling

## Key Components

1. **EventPublisherManager** - Centralized event management
2. **EventPublisher** - Base class for event publishers
3. **RunState** - Current state of browser automation runs
4. **RunEvent** - Base event for state changes

## Usage Examples

```python
from bugninja.events import EventPublisherManager
from bugninja.events.types import EventPublisherType

# Create event manager with rich terminal publisher
event_manager = EventPublisherManager([
    EventPublisherFactory.create_publishers(
        [EventPublisherType.RICH_TERMINAL], {}
    )
])

# Initialize run tracking
run_id = await event_manager.initialize_run(
    run_type="navigation",
    metadata={"task": "Login flow"}
)
```
"""

from .base import EventPublisher
from .manager import EventPublisherManager
from .factory import EventPublisherFactory
from .types import EventPublisherType
from .models import RunEvent, RunState
from .exceptions import PublisherUnavailableError

__all__ = [
    "EventPublisher",
    "EventPublisherManager",
    "EventPublisherFactory",
    "EventPublisherType",
    "RunEvent",
    "RunState",
    "PublisherUnavailableError",
]
