"""
Event publisher implementations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from redis import Redis
from redis.exceptions import ConnectionError

from .base import EventPublisher
from .exceptions import PublisherUnavailableError
from .models import RunEvent, RunState
from .types import RunStatus, RunType


class NullEventPublisher(EventPublisher):
    """No-op event publisher for when no tracking is needed."""

    def __init__(self) -> None:
        self._available = True

    def is_available(self) -> bool:
        """Check if null publisher is available (always True)."""
        return self._available

    async def initialize_run(self, run_type: str, metadata: Dict[str, Any]) -> str:
        """Initialize a run (no-op implementation).

        Args:
            run_type: Type of run
            metadata: Run metadata

        Returns:
            Generated run ID

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Null publisher is not available")
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


class RedisEventPublisher(EventPublisher):
    """Redis-based event publisher with availability checking."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Redis is available."""
        try:
            if self.redis and self.redis.ping():
                self._available = True
            else:
                self._available = False
        except Exception:
            self._available = False

    def is_available(self) -> bool:
        """Check if Redis publisher is available."""
        # Re-check availability periodically
        self._check_availability()
        return self._available

    async def initialize_run(self, run_type: str, metadata: Dict[str, Any]) -> str:
        """Initialize a run in Redis.

        Args:
            run_type: Type of run
            metadata: Run metadata

        Returns:
            Generated run ID

        Raises:
            PublisherUnavailableError: If Redis is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Redis publisher is not available")

        run_id = f"run_{uuid.uuid4().hex[:8]}"

        # Create initial state
        state = RunState(
            run_id=run_id,
            run_type=RunType(run_type),
            status=RunStatus.RUNNING,
            start_time=datetime.utcnow(),
            last_update_time=datetime.utcnow(),
            task_description=metadata.get("task_description"),
            metadata=metadata,
        )

        # Save to Redis
        try:
            self.redis.setex(
                f"bugninja:runs:{run_id}",
                86400,  # 24 hours TTL
                state.model_dump_json(),
            )

            # Add to active runs set
            self.redis.sadd("bugninja:runs:active", run_id)

        except ConnectionError:
            self._available = False
            raise PublisherUnavailableError("Redis connection failed")

        return run_id

    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update run state in Redis.

        Args:
            run_id: ID of the run to update
            state: New state of the run

        Raises:
            PublisherUnavailableError: If Redis is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Redis publisher is not available")

        try:
            # Update state in Redis
            self.redis.setex(
                f"bugninja:runs:{run_id}",
                86400,  # 24 hours TTL
                state.model_dump_json(),
            )

            # Update status sets
            self._update_status_sets(run_id, state.status)

        except ConnectionError:
            self._available = False
            raise PublisherUnavailableError("Redis connection failed")

    async def complete_run(self, run_id: str, success: bool, error: Optional[str] = None) -> None:
        """Complete run in Redis.

        Args:
            run_id: ID of the run to complete
            success: Whether the run was successful
            error: Error message if run failed

        Raises:
            PublisherUnavailableError: If Redis is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Redis publisher is not available")

        try:
            # Get current state
            state_data = self.redis.get(f"bugninja:runs:{run_id}")
            if state_data:
                state = RunState.model_validate_json(state_data)  # type:ignore

                # Update state
                state.status = RunStatus.COMPLETED if success else RunStatus.FAILED
                state.last_update_time = datetime.utcnow()
                if error:
                    state.error_message = error

                # Save updated state
                self.redis.setex(
                    f"bugninja:runs:{run_id}",
                    86400,  # 24 hours TTL
                    state.model_dump_json(),
                )

                # Update status sets
                self._update_status_sets(run_id, state.status)

        except ConnectionError:
            self._available = False
            raise PublisherUnavailableError("Redis connection failed")

    async def publish_event(self, event: RunEvent) -> None:
        """Publish event to Redis.

        Args:
            event: Event to publish

        Raises:
            PublisherUnavailableError: If Redis is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Redis publisher is not available")

        try:
            # Store event in Redis
            event_key = f"bugninja:events:{event.run_id}:{event.timestamp.isoformat()}"
            self.redis.setex(
                event_key,
                86400,  # 24 hours TTL
                event.model_dump_json(),
            )

        except ConnectionError:
            self._available = False
            raise PublisherUnavailableError("Redis connection failed")

    def _update_status_sets(self, run_id: str, status: str) -> None:
        """Update Redis status sets."""
        try:
            pipeline = self.redis.pipeline()

            # Remove from all status sets
            pipeline.srem("bugninja:runs:active", run_id)
            pipeline.srem("bugninja:runs:completed", run_id)
            pipeline.srem("bugninja:runs:failed", run_id)

            # Add to appropriate status set
            if status == RunStatus.RUNNING:
                pipeline.sadd("bugninja:runs:active", run_id)
            elif status == RunStatus.COMPLETED:
                pipeline.sadd("bugninja:runs:completed", run_id)
            elif status == RunStatus.FAILED:
                pipeline.sadd("bugninja:runs:failed", run_id)

            pipeline.execute()

        except ConnectionError:
            self._available = False
