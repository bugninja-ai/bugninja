"""
Event models for the event publishing system.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from .types import RunStatus, RunType


class RunState(BaseModel):
    """Current state of a run (replaces RunProgressState).

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

    # Healing Specific (kept from RunProgressState)
    healing_started_at: Optional[datetime] = None
    original_traversal_file: Optional[str] = None

    # Task Context (kept from RunProgressState)
    task_description: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration for RunState."""

        use_enum_values = True
