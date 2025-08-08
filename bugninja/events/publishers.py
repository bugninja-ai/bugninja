"""
Event publisher implementations.
"""

import uuid
from typing import Any, Dict, Optional

from .base import EventPublisher
from .exceptions import PublisherUnavailableError
from .models import RunEvent, RunState


class NullEventPublisher(EventPublisher):
    """No-op event publisher for when no tracking is needed."""

    def __init__(self) -> None:
        self._available = True

    def is_available(self) -> bool:
        """Check if null publisher is available (always True)."""
        return self._available

    async def initialize_run(
        self, run_type: str, metadata: Dict[str, Any], existing_run_id: Optional[str] = None
    ) -> str:
        """Initialize a run (no-op implementation).

        Args:
            run_type: Type of run
            metadata: Run metadata
            existing_run_id: Optional existing run ID to use instead of generating new one

        Returns:
            Generated run ID or existing run ID

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Null publisher is not available")

        if existing_run_id:
            return existing_run_id
        return f"null_run_{uuid.uuid4().hex[:8]}"

    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update run state (no-op implementation).

        Args:
            run_id: ID of the run to update
            state: New state of the run

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Null publisher is not available")
        # Do nothing - this is a no-op publisher

    async def complete_run(self, run_id: str, success: bool, error: Optional[str] = None) -> None:
        """Complete run (no-op implementation).

        Args:
            run_id: ID of the run to complete
            success: Whether the run was successful
            error: Error message if run failed

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Null publisher is not available")
        # Do nothing - this is a no-op publisher

    async def publish_event(self, event: RunEvent) -> None:
        """Publish event (no-op implementation).

        Args:
            event: Event to publish

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Null publisher is not available")
        # Do nothing - this is a no-op publisher
