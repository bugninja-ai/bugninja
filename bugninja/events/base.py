"""
Abstract base class for event publishers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from browser_use.agent.views import AgentBrain  # type: ignore

from bugninja.events.models import RunState
from bugninja.schemas.pipeline import BugninjaExtendedAction


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
        raise NotImplementedError("is_available() must be implemented by subclasses")

    @abstractmethod
    async def initialize_run(
        self, run_type: str, metadata: Dict[str, Any], existing_run_id: Optional[str] = None
    ) -> str:
        """Initialize a new run and return run_id.

        Args:
            run_type: Type of run ("navigation", "replay", "healing")
            metadata: Additional metadata for the run
            existing_run_id: Optional existing run ID to use instead of generating new one

        Returns:
            Unique run ID (either existing or generated)

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        raise NotImplementedError("initialize_run() must be implemented by subclasses")

    @abstractmethod
    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update the state of a run.

        Args:
            run_id: ID of the run to update
            state: New state of the run

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        raise NotImplementedError("update_run_state() must be implemented by subclasses")

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
        raise NotImplementedError("complete_run() must be implemented by subclasses")

    @abstractmethod
    async def publish_action_event(
        self,
        run_id: str,
        brain_state_id: str,
        actual_brain_state: AgentBrain,
        action_result_data: BugninjaExtendedAction,
    ) -> None:
        """Publish a run event.

        Args:
            event: Event to publish

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        raise NotImplementedError("publish_event() must be implemented by subclasses")
