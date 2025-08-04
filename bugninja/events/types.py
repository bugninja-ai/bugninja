"""
Event types and enumerations for the event publishing system.
"""

from enum import Enum


class EventPublisherType(str, Enum):
    """Supported event publisher types."""

    NULL = "null"  # No-op publisher for testing/development
    REDIS = "redis"  # Redis-based publisher
    RICH_TERMINAL = "rich_terminal"  # Rich terminal output publisher
    # Future: RABBITMQ = "rabbitmq"
    # Future: KAFKA = "kafka"
    # Future: FILE = "file"


class RunType(str, Enum):
    """Types of browser automation runs."""

    NAVIGATION = "navigation"  # Initial traversal
    REPLAY = "replay"  # Session replay
    HEALING = "healing"  # Healing process


class RunStatus(str, Enum):
    """Status of browser automation runs."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    """Types of events that can be published."""

    RUN_STARTED = "run_started"
    STEP_COMPLETED = "step_completed"
    ACTION_COMPLETED = "action_completed"
    HEALING_STARTED = "healing_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
