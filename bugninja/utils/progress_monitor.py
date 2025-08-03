"""
Progress monitor for Bugninja runs.

This module provides utilities for monitoring the progress of
browser automation runs with optional Redis support.
"""

from typing import Any, Dict, List, Optional

from redis import Redis
from redis.exceptions import ConnectionError

from bugninja.schemas.progress import RunProgressState


class ProgressMonitor:
    """Monitor for browser automation run progress."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self._enabled = redis_client is not None

    def is_enabled(self) -> bool:
        """Check if progress monitoring is enabled."""
        return self._enabled and self.redis is not None

    def get_run_status(self, run_id: str) -> Optional[RunProgressState]:
        """Get status of a specific run (only if enabled)."""
        if not self.is_enabled() or not self.redis:
            return None

        try:
            data = self.redis.get(f"bugninja:runs:{run_id}")
            if data and isinstance(data, str):
                return RunProgressState.model_validate_json(data)
        except ConnectionError:
            self._enabled = False
        return None

    def get_active_runs(self) -> List[RunProgressState]:
        """Get all currently active runs (only if enabled)."""
        if not self.is_enabled() or not self.redis:
            return []

        try:
            active_run_ids = self.redis.smembers("bugninja:runs:active")
            if not isinstance(active_run_ids, set):
                return []
            runs = []
            for run_id in active_run_ids:
                if isinstance(run_id, bytes):
                    run_id_str = run_id.decode()
                else:
                    run_id_str = str(run_id)
                state = self.get_run_status(run_id_str)
                if state:
                    runs.append(state)
            return runs
        except ConnectionError:
            self._enabled = False
            return []

    def get_completed_runs(self) -> List[RunProgressState]:
        """Get all completed runs (only if enabled)."""
        if not self.is_enabled() or not self.redis:
            return []

        try:
            completed_run_ids = self.redis.smembers("bugninja:runs:completed")
            if not isinstance(completed_run_ids, set):
                return []
            runs = []
            for run_id in completed_run_ids:
                if isinstance(run_id, bytes):
                    run_id_str = run_id.decode()
                else:
                    run_id_str = str(run_id)
                state = self.get_run_status(run_id_str)
                if state:
                    runs.append(state)
            return runs
        except ConnectionError:
            self._enabled = False
            return []

    def get_failed_runs(self) -> List[RunProgressState]:
        """Get all failed runs (only if enabled)."""
        if not self.is_enabled() or not self.redis:
            return []

        try:
            failed_run_ids = self.redis.smembers("bugninja:runs:failed")
            if not isinstance(failed_run_ids, set):
                return []
            runs = []
            for run_id in failed_run_ids:
                if isinstance(run_id, bytes):
                    run_id_str = run_id.decode()
                else:
                    run_id_str = str(run_id)
                state = self.get_run_status(run_id_str)
                if state:
                    runs.append(state)
            return runs
        except ConnectionError:
            self._enabled = False
            return []

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get a summary of run progress (only if enabled)."""
        if not self.is_enabled():
            return {"error": "Progress tracking not enabled"}

        state = self.get_run_status(run_id)
        if not state:
            return {"error": "Run not found"}

        summary = {
            "run_id": state.run_id,
            "run_type": state.run_type,
            "status": state.status,
            "current_step": state.current_step,
            "current_action": state.current_action,
            "current_url": state.current_url,
            "start_time": state.start_time.isoformat(),
            "last_update": state.last_update_time.isoformat(),
        }

        # Add type-specific information
        if state.run_type == "replay":
            summary["progress_percentage"] = state.progress_percentage
            summary["total_steps"] = state.total_steps
        elif state.run_type == "healing":
            summary["healing_started_at"] = (
                state.healing_started_at.isoformat() if state.healing_started_at else None
            )

        # Add error information if failed
        if state.status == "failed":
            summary["error_message"] = state.error_message

        return summary

    def get_all_runs_summary(self) -> Dict[str, Any]:
        """Get summary of all runs (only if enabled)."""
        if not self.is_enabled():
            return {"error": "Progress tracking not enabled"}

        try:
            active_runs = self.get_active_runs()
            completed_runs = self.get_completed_runs()
            failed_runs = self.get_failed_runs()

            return {
                "active_runs_count": len(active_runs),
                "completed_runs_count": len(completed_runs),
                "failed_runs_count": len(failed_runs),
                "total_runs_count": len(active_runs) + len(completed_runs) + len(failed_runs),
                "active_runs": [run.run_id for run in active_runs],
                "recent_completed": [run.run_id for run in completed_runs[-5:]],  # Last 5 completed
                "recent_failed": [run.run_id for run in failed_runs[-5:]],  # Last 5 failed
            }
        except ConnectionError:
            self._enabled = False
            return {"error": "Redis connection lost"}
