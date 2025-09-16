"""
Progress tracking schemas for Bugninja.

This module provides Pydantic models for tracking the progress of
browser automation runs with optional Redis support.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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


class RunProgressState(BaseModel):
    """Progress state for a browser automation run.

    This model tracks the current state of a browser automation run including
    progress information, timing, and error details.
    """

    # Core Identification
    run_id: str
    run_type: RunType
    status: RunStatus

    # Progress Tracking
    current_step: int = 0
    total_steps: Optional[int] = None  # None for navigation/healing
    progress_percentage: Optional[float] = None  # Only for replays

    # Current Context
    current_action: Optional[str] = None
    current_url: Optional[str] = None

    # Timing
    start_time: datetime
    last_update_time: datetime

    # Error Handling
    error_message: Optional[str] = None

    # Healing Specific
    healing_started_at: Optional[datetime] = None
    original_traversal_file: Optional[str] = None

    # Task Context
    task_description: Optional[str] = None

    class Config:
        """Pydantic configuration for RunProgressState."""

        use_enum_values = True
