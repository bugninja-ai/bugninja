"""
Progress tracker for Bugninja runs.

This module provides optional progress tracking for browser automation runs
using Redis for state management.
"""

import uuid
from datetime import datetime
from typing import Optional

from redis import Redis
from redis.exceptions import ConnectionError

from bugninja.schemas.progress import RunProgressState, RunStatus, RunType


class ProgressTracker:
    """Optional progress tracker for browser automation runs."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self.run_id = None
        self.state: Optional[RunProgressState] = None
        self._enabled = redis_client is not None

    def is_enabled(self) -> bool:
        """Check if progress tracking is enabled (Redis available)."""
        return self._enabled and self.redis is not None

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return f"run_{uuid.uuid4().hex[:8]}"

    def initialize_navigation_run(self, task_description: str) -> Optional[str]:
        """Initialize a navigation run (only if Redis is available)."""
        if not self.is_enabled():
            return None

        run_id = self._generate_run_id()

        self.state = RunProgressState(
            run_id=run_id,
            run_type=RunType.NAVIGATION,
            status=RunStatus.RUNNING,
            start_time=datetime.utcnow(),
            last_update_time=datetime.utcnow(),
            task_description=task_description,
            current_step=0,
            total_steps=None,
            progress_percentage=None,
        )

        self._save_state()
        return run_id

    def initialize_replay_run(self, traversal_file: str, total_actions: int) -> Optional[str]:
        """Initialize a replay run (only if Redis is available)."""
        if not self.is_enabled():
            return None

        run_id = self._generate_run_id()

        self.state = RunProgressState(
            run_id=run_id,
            run_type=RunType.REPLAY,
            status=RunStatus.RUNNING,
            start_time=datetime.utcnow(),
            last_update_time=datetime.utcnow(),
            current_step=0,
            total_steps=total_actions,
            progress_percentage=0.0,
            original_traversal_file=traversal_file,
        )

        self._save_state()
        return run_id

    async def update_step(self, step_number: int, action_type: str, current_url: str) -> None:
        """Update progress for current step (only if enabled)."""
        if not self.is_enabled() or not self.state:
            return

        try:
            self.state.current_step = step_number
            self.state.current_action = action_type
            self.state.current_url = current_url
            self.state.last_update_time = datetime.utcnow()

            # Calculate percentage only for replays
            if self.state.run_type == RunType.REPLAY and self.state.total_steps:
                self.state.progress_percentage = (step_number / self.state.total_steps) * 100

            self._save_state()
        except ConnectionError:
            # Redis connection lost, disable tracking
            self._enabled = False

    async def start_healing(self) -> None:
        """Transition to healing mode (only if enabled)."""
        if not self.is_enabled() or not self.state:
            return

        try:
            self.state.run_type = RunType.HEALING
            self.state.healing_started_at = datetime.utcnow()
            self.state.progress_percentage = None
            self.state.total_steps = None

            self._save_state()
        except ConnectionError:
            self._enabled = False

    async def complete_run(self, success: bool, error_message: Optional[str] = None) -> None:
        """Complete the run (only if enabled)."""
        if not self.is_enabled() or not self.state:
            return

        try:
            if success:
                self.state.status = RunStatus.COMPLETED
            else:
                self.state.status = RunStatus.FAILED
                self.state.error_message = error_message

            self.state.last_update_time = datetime.utcnow()
            self._save_state()
        except ConnectionError:
            self._enabled = False

    def _save_state(self) -> None:
        """Save current state to Redis (with error handling)."""
        if not self.is_enabled() or not self.state or not self.redis:
            return

        try:
            self.redis.setex(
                f"bugninja:runs:{self.state.run_id}",
                86400,  # 24 hours TTL
                self.state.model_dump_json(),
            )

            self._update_status_sets()
        except ConnectionError:
            # Redis connection lost, disable tracking
            self._enabled = False

    def _update_status_sets(self) -> None:
        """Update Redis sets for different statuses (with error handling)."""
        if not self.is_enabled() or not self.state or not self.redis:
            return

        try:
            pipeline = self.redis.pipeline()

            # Remove from all status sets
            pipeline.srem("bugninja:runs:active", self.state.run_id)
            pipeline.srem("bugninja:runs:completed", self.state.run_id)
            pipeline.srem("bugninja:runs:failed", self.state.run_id)

            # Add to appropriate status set
            if self.state.status == RunStatus.RUNNING:
                pipeline.sadd("bugninja:runs:active", self.state.run_id)
            elif self.state.status == RunStatus.COMPLETED:
                pipeline.sadd("bugninja:runs:completed", self.state.run_id)
            elif self.state.status == RunStatus.FAILED:
                pipeline.sadd("bugninja:runs:failed", self.state.run_id)

            pipeline.execute()  # type: ignore[no-untyped-call]
        except ConnectionError:
            self._enabled = False
