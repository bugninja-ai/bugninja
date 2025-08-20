"""
Thread-safe manager for multiple event publishers.
"""

import asyncio
from threading import Lock
from typing import Any, Dict, List, Optional

from browser_use.agent.views import AgentBrain  # type: ignore

from bugninja.schemas.pipeline import BugninjaExtendedAction

from .base import EventPublisher
from .exceptions import PublisherUnavailableError
from .models import RunState


class EventPublisherManager:
    """Thread-safe manager for multiple event publishers.

    This class manages multiple event publishers and ensures thread-safe
    operations across different runs and publishers.
    """

    def __init__(self, publishers: List[EventPublisher]):
        """Initialize the event publisher manager.

        Args:
            publishers: List of event publishers to manage
        """
        self.publishers = publishers
        self._lock = Lock()
        self._run_publishers: Dict[str, List[EventPublisher]] = {}

    def get_available_publishers(self) -> List[EventPublisher]:
        """Get list of available publishers.

        Returns:
            List of publishers that are available and ready
        """
        with self._lock:
            return [p for p in self.publishers if p.is_available()]

    async def initialize_run(
        self, run_type: str, metadata: Dict[str, Any], existing_run_id: Optional[str] = None
    ) -> str:
        """Initialize a run across all available publishers.

        Args:
            run_type: Type of run
            metadata: Run metadata
            existing_run_id: Optional existing run ID to use instead of generating new one

        Returns:
            Run ID (either existing or generated)

        Raises:
            PublisherUnavailableError: If no publishers are available
        """
        available_publishers = self.get_available_publishers()

        if not available_publishers:
            raise PublisherUnavailableError("No event publishers are available")

        # Use existing run_id if provided, otherwise generate new one
        if existing_run_id:
            run_id = existing_run_id
        else:
            run_id = await available_publishers[0].initialize_run(run_type, metadata)

        # Initialize run in all available publishers
        with self._lock:
            self._run_publishers[run_id] = available_publishers.copy()

        # Initialize run in all publishers
        for publisher in available_publishers:
            try:
                if existing_run_id:
                    # Use existing run_id for all publishers
                    await publisher.initialize_run(run_type, metadata, existing_run_id)
                else:
                    # Only first publisher generates run_id, others use it
                    if publisher != available_publishers[0]:
                        await publisher.initialize_run(run_type, metadata)
            except Exception:
                # Remove failed publisher from this run's publishers
                with self._lock:
                    if run_id in self._run_publishers:
                        self._run_publishers[run_id] = [
                            p for p in self._run_publishers[run_id] if p != publisher
                        ]

        return run_id

    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update run state across all publishers for this run.

        Args:
            run_id: ID of the run to update
            state: New state of the run
        """
        with self._lock:
            publishers = self._run_publishers.get(run_id, [])

        # Update state in all publishers for this run
        tasks = []
        for publisher in publishers:
            if publisher.is_available():
                tasks.append(publisher.update_run_state(run_id, state))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def complete_run(self, run_id: str, success: bool, error: Optional[str] = None) -> None:
        """Complete run across all publishers for this run.

        Args:
            run_id: ID of the run to complete
            success: Whether the run was successful
            error: Error message if run failed
        """
        with self._lock:
            publishers = self._run_publishers.get(run_id, [])

        # Complete run in all publishers for this run
        tasks = []
        for publisher in publishers:
            if publisher.is_available():
                tasks.append(publisher.complete_run(run_id, success, error))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up run publishers
        with self._lock:
            self._run_publishers.pop(run_id, None)

    async def publish_action_event(
        self,
        run_id: str,
        brain_state_id: str,
        actual_brain_state: AgentBrain,
        action_result_data: BugninjaExtendedAction,
    ) -> None:

        with self._lock:
            publishers = self._run_publishers.get(run_id, [])

        # Publish event to all publishers for this run
        tasks = []
        for publisher in publishers:
            if publisher.is_available():
                tasks.append(
                    publisher.publish_action_event(
                        run_id=run_id,
                        brain_state_id=brain_state_id,
                        actual_brain_state=actual_brain_state,
                        action_result_data=action_result_data,
                    )
                )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def has_publishers(self) -> bool:
        """Check if any publishers are available.

        Returns:
            True if at least one publisher is available
        """
        return len(self.get_available_publishers()) > 0
