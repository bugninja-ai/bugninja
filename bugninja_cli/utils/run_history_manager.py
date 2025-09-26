"""
Run history management utilities for Bugninja CLI.

This module provides utilities for managing run history data in JSON files,
separating run history from task configuration for better separation of concerns.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from cuid2 import Cuid as CUID

if TYPE_CHECKING:
    from bugninja.schemas import TaskExecutionResult


class RunHistoryManager:
    """Manager for task run history stored in JSON files.

    This class provides comprehensive run history management including
    loading, saving, and updating run history data in JSON format.
    """

    def __init__(self, task_path: Path):
        """Initialize the RunHistoryManager with task path.

        Args:
            task_path (Path): Path to the task directory
        """
        self.task_path = task_path
        self.run_history_path = task_path / "run_history.json"

    def load_history(self) -> Dict[str, Any]:
        """Load run history from JSON file.

        Returns:
            Dict[str, Any]: Run history data

        Raises:
            FileNotFoundError: If run history file doesn't exist
            ValueError: If JSON file is corrupted or invalid
        """
        if not self.run_history_path.exists():
            raise FileNotFoundError(f"Run history file not found: {self.run_history_path}")

        try:
            with open(self.run_history_path, "r", encoding="utf-8") as f:
                loaded_file: Dict[str, Any] = json.load(f)
                return loaded_file
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Corrupted run history file: {self.run_history_path}. "
                f"Please delete or correct the file. Error: {e}"
            )
        except Exception as e:
            raise ValueError(f"Failed to load run history: {e}")

    def save_history(self, history_data: Dict[str, Any]) -> None:
        """Save run history to JSON file with atomic write.

        Args:
            history_data (Dict[str, Any]): Run history data to save

        Raises:
            ValueError: If saving fails
        """
        try:
            # Ensure task directory exists
            self.task_path.mkdir(parents=True, exist_ok=True)

            # Atomic write: write to temp file first, then rename
            temp_path = self.run_history_path.with_suffix(".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.run_history_path)

        except Exception as e:
            raise ValueError(f"Failed to save run history: {e}")

    def create_initial_history(self, task_id: str) -> Dict[str, Any]:
        """Create initial run history structure.

        Args:
            task_id (str): Task CUID2 identifier

        Returns:
            Dict[str, Any]: Initial run history structure
        """
        return {
            "task_id": task_id,
            "created_date": datetime.now(UTC).isoformat() + "Z",
            "ai_navigated_runs": [],
            "replay_runs": [],
            "summary": {
                "total_ai_runs": 0,
                "total_replay_runs": 0,
                "successful_ai_runs": 0,
                "successful_replay_runs": 0,
            },
        }

    def add_ai_run(self, result: TaskExecutionResult) -> None:
        """Add an AI-navigated run to the history.

        Args:
            result (TaskExecutionResult): Execution result to add
        """
        # Load existing history or create new
        try:
            history = self.load_history()
        except FileNotFoundError:
            # Create initial history if file doesn't exist
            task_id = self._get_task_id_from_toml()
            history = self.create_initial_history(task_id)

        # Create run entry
        run_entry = self._create_ai_run_entry(result)
        history["ai_navigated_runs"].append(run_entry)

        # Update summary
        self._update_summary(history)

        # Save back
        self.save_history(history)

    def add_replay_run(
        self, result: TaskExecutionResult, original_traversal_id: str, healing_enabled: bool
    ) -> None:
        """Add a replay run to the history.

        Args:
            result (TaskExecutionResult): Execution result to add
            original_traversal_id (str): ID of the original traversal
            healing_enabled (bool): Whether healing was enabled
        """
        # Load existing history or create new
        try:
            history = self.load_history()
        except FileNotFoundError:
            # Create initial history if file doesn't exist
            task_id = self._get_task_id_from_toml()
            history = self.create_initial_history(task_id)

        # Create replay entry
        replay_entry = self._create_replay_run_entry(result, original_traversal_id, healing_enabled)
        history["replay_runs"].append(replay_entry)

        # Update summary
        self._update_summary(history)

        # Save back
        self.save_history(history)

    def get_latest_ai_run_traversal(self) -> Optional[Path]:
        """Get the path to the latest AI-navigated run traversal.

        Returns:
            Optional[Path]: Path to latest traversal, or None if no runs
        """
        try:
            history = self.load_history()
            ai_runs = history.get("ai_navigated_runs", [])

            if not ai_runs:
                return None

            # Get the latest run (last in the list)
            latest_run: Dict[str, Any] = ai_runs[-1]
            traversal_path_str: str = latest_run.get("traversal_path", "")

            if not len(traversal_path_str):
                return None

            # Handle both relative and absolute paths
            if traversal_path_str.startswith("/"):
                return Path(traversal_path_str)
            else:
                return self.task_path / traversal_path_str

        except (FileNotFoundError, ValueError):
            return None

    def _get_task_id_from_toml(self) -> str:
        """Get task ID from the task TOML file.

        Returns:
            str: Task ID from TOML file, or 'unknown' if not found
        """
        try:
            import tomli

            # Find the task TOML file in the task directory
            toml_files = list(self.task_path.glob("task_*.toml"))
            if not toml_files:
                return "unknown"

            # Use the first TOML file found
            toml_file = toml_files[0]

            with open(toml_file, "rb") as f:
                config = tomli.load(f)

            # Get task ID from metadata section
            metadata: Dict[str, str] = config.get("metadata", {})
            return metadata.get("task_id", "unknown")

        except Exception:
            return "unknown"

    def _create_ai_run_entry(self, result: TaskExecutionResult) -> Dict[str, Any]:
        """Create an AI-navigated run entry.

        Args:
            result (TaskExecutionResult): Execution result

        Returns:
            Dict[str, Any]: Run entry dictionary
        """
        run_id = CUID().generate()
        timestamp = datetime.now(UTC).isoformat()

        run_entry = {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "success" if result.success else "failed",
            "traversal_path": str(result.traversal_path) if result.traversal_path else "",
            "execution_time": result.execution_time,
        }

        # Only add error_message if it's not None and not empty
        if result.error_message is not None and result.error_message.strip():
            run_entry["error_message"] = result.error_message

        return run_entry

    def _create_replay_run_entry(
        self, result: TaskExecutionResult, original_traversal_id: str, healing_enabled: bool
    ) -> Dict[str, Any]:
        """Create a replay run entry.

        Args:
            result (TaskExecutionResult): Execution result
            original_traversal_id (str): ID of the original traversal
            healing_enabled (bool): Whether healing was enabled

        Returns:
            Dict[str, Any]: Replay run entry dictionary
        """
        run_id = CUID().generate()
        timestamp = datetime.now(UTC).isoformat()

        replay_entry = {
            "run_id": run_id,
            "timestamp": timestamp,
            "status": "success" if result.success else "failed",
            "traversal_path": str(result.traversal_path) if result.traversal_path else "",
            "execution_time": result.execution_time,
            "original_traversal_id": original_traversal_id,
            "healing_enabled": healing_enabled,
        }

        # Only add error_message if it's not None and not empty
        if result.error_message is not None and result.error_message.strip():
            replay_entry["error_message"] = result.error_message

        return replay_entry

    def _update_summary(self, history: Dict[str, Any]) -> None:
        """Update summary statistics in the history.

        Args:
            history (Dict[str, Any]): History data to update
        """
        ai_runs = history.get("ai_navigated_runs", [])
        replay_runs = history.get("replay_runs", [])

        history["summary"] = {
            "total_ai_runs": len(ai_runs),
            "total_replay_runs": len(replay_runs),
            "successful_ai_runs": sum(1 for run in ai_runs if run["status"] == "success"),
            "successful_replay_runs": sum(1 for run in replay_runs if run["status"] == "success"),
        }
