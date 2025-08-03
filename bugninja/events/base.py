"""
Abstract base class for event publishers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .models import RunEvent, RunState


class EventPublisher(ABC):
    """Abstract base class for event publishers.

    This class defines the interface for publishing run events to various
    backends (Redis, RabbitMQ, files, etc.). Multiple publishers can be
    used simultaneously with thread-safe operations.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the publisher is available and ready to use.

        Returns:
            True if publisher is available, False otherwise
        """
        pass

    @abstractmethod
    async def initialize_run(self, run_type: str, metadata: Dict[str, Any]) -> str:
        """Initialize a new run and return run_id.

        Args:
            run_type: Type of run ("navigation", "replay", "healing")
            metadata: Additional metadata for the run

        Returns:
            Unique run ID

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        pass

    @abstractmethod
    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update the state of a run.

        Args:
            run_id: ID of the run to update
            state: New state of the run

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        pass

    @abstractmethod
    async def complete_run(self, run_id: str, success: bool, error: Optional[str] = None) -> None:
        """Mark a run as completed.

        Args:
            run_id: ID of the run to complete
            success: Whether the run was successful
            error: Error message if run failed

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        pass

    @abstractmethod
    async def publish_event(self, event: RunEvent) -> None:
        """Publish a run event.

        Args:
            event: Event to publish

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        pass
