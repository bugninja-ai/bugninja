"""
Statistics collection utilities for Bugninja CLI.

This module provides utilities for collecting and aggregating statistics
from task run history data across a Bugninja project.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bugninja_cli.utils.run_history_manager import RunHistoryManager


class TaskStats:
    """Statistics for a single task."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.ai_runs = 0
        self.replay_runs = 0
        self.total_runs = 0
        self.last_status = "Never"
        self.last_run_time = "-"
        self.last_run_timestamp: Optional[datetime] = None
        self.last_run_type = "-"
        self.error_type = "-"
        self.creation_type = "-"


class StatsCollector:
    """Collects statistics from task run history data."""

    def __init__(self, project_root: Path):
        """Initialize the stats collector.

        Args:
            project_root: Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.tasks_dir = project_root / "tasks"

    def collect_all_task_stats(self) -> List[TaskStats]:
        """Collect statistics for all tasks in the project.

        Returns:
            List of TaskStats objects for each task, ordered by creation date
        """
        if not self.tasks_dir.exists():
            return []

        task_stats = []

        # Get all task directories and collect their creation dates
        task_dirs_with_dates = []
        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            # Get creation date from task TOML file
            creation_date = self._get_task_creation_date(task_dir)
            task_dirs_with_dates.append((task_dir, creation_date))

        # Sort by creation date (oldest first)
        # Convert all datetimes to timezone-naive for comparison
        task_dirs_with_dates.sort(key=lambda x: x[1].replace(tzinfo=None) if x[1].tzinfo else x[1])

        # Collect stats for each task
        for task_dir, _ in task_dirs_with_dates:
            task_name = task_dir.name
            stats = self._collect_task_stats(task_dir, task_name)
            task_stats.append(stats)

        return task_stats

    def _collect_task_stats(self, task_dir: Path, task_name: str) -> TaskStats:
        """Collect statistics for a single task.

        Args:
            task_dir: Directory containing the task
            task_name: Name of the task

        Returns:
            TaskStats object with collected data
        """
        stats = TaskStats(task_name)

        try:
            # Load creation type from TOML file
            stats.creation_type = self._get_task_creation_type(task_dir)

            # Use RunHistoryManager to load the history
            history_manager = RunHistoryManager(task_dir)
            history_data = history_manager.load_history()

            # Extract AI runs
            ai_runs = history_data.get("ai_navigated_runs", [])
            stats.ai_runs = len(ai_runs)

            # Extract replay runs
            replay_runs = history_data.get("replay_runs", [])
            stats.replay_runs = len(replay_runs)

            # Calculate total
            stats.total_runs = stats.ai_runs + stats.replay_runs

            # Find the most recent run (from both AI and replay runs)
            all_runs = []

            # Add AI runs with type indicator
            for run in ai_runs:
                run_copy = run.copy()
                run_copy["run_type"] = "ai"
                all_runs.append(run_copy)

            # Add replay runs with type indicator
            for run in replay_runs:
                run_copy = run.copy()
                run_copy["run_type"] = "replay"
                all_runs.append(run_copy)

            if all_runs:
                # Sort by timestamp to get the most recent
                all_runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                latest_run = all_runs[0]

                # Set last status
                status = latest_run.get("status", "unknown")
                if status == "success":
                    stats.last_status = "✅ Success"
                elif status == "failed":
                    stats.last_status = "❌ Failed"
                else:
                    stats.last_status = f"❓ {status.title()}"

                # Set last run type
                run_type = latest_run.get("run_type", "unknown")
                if run_type == "ai":
                    stats.last_run_type = "Agentic"
                elif run_type == "replay":
                    stats.last_run_type = "Replay"
                else:
                    stats.last_run_type = run_type.title()

                # Set error type if available
                error_message = latest_run.get("error_message", "")
                if error_message and status == "failed":
                    # Extract error type from error message
                    if "validation_error" in error_message:
                        stats.error_type = "Validation Error"
                    elif "session_replay_error" in error_message:
                        stats.error_type = "Replay Error"
                    elif "Environment configuration error" in error_message:
                        stats.error_type = "Config Error"
                    else:
                        stats.error_type = "Other Error"
                else:
                    stats.error_type = "-"

                # Set last run time
                timestamp_str = latest_run.get("timestamp", "")
                if timestamp_str:
                    try:
                        # Parse ISO timestamp
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1] + "+00:00"
                        stats.last_run_timestamp = datetime.fromisoformat(timestamp_str)
                        stats.last_run_time = stats.last_run_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        stats.last_run_time = timestamp_str
            else:
                stats.last_status = "⏸️ Never"
                stats.last_run_time = "-"
                stats.last_run_type = "-"
                stats.error_type = "-"

        except FileNotFoundError:
            # Handle missing run history files - task has never been run
            stats.last_status = "⏸️ Never"
            stats.last_run_time = "-"
            stats.last_run_type = "-"
            stats.error_type = "-"
        except (ValueError, json.JSONDecodeError):
            # Handle corrupted run history files
            stats.last_status = "⚠️ Error"
            stats.last_run_time = "-"
            stats.last_run_type = "-"
            stats.error_type = "-"

        return stats

    def _get_task_creation_date(self, task_dir: Path) -> datetime:
        """Get the creation date of a task from its TOML file.

        Args:
            task_dir: Directory containing the task

        Returns:
            Creation date of the task, or current time if not found
        """
        try:
            import tomli

            # Find the task TOML file
            toml_files = list(task_dir.glob("task_*.toml"))
            if not toml_files:
                return datetime.now()

            # Use the first TOML file found
            toml_file = toml_files[0]

            with open(toml_file, "rb") as f:
                config = tomli.load(f)

            # Get creation date from metadata section
            metadata = config.get("metadata", {})
            created_date_str = metadata.get("created_date", "")

            if created_date_str:
                try:
                    # Clean up the date string - handle various formats
                    # Handle +00:00Z format (timezone + Z)
                    if created_date_str.endswith("+00:00Z"):
                        created_date_str = created_date_str[:-1]  # Remove the Z
                    elif created_date_str.endswith("Z"):
                        created_date_str = created_date_str[:-1] + "+00:00"

                    parsed_date = datetime.fromisoformat(created_date_str)
                    return parsed_date
                except (ValueError, TypeError):
                    pass

            # Fallback to file modification time
            return datetime.fromtimestamp(toml_file.stat().st_mtime)

        except Exception:
            # Fallback to current time if anything goes wrong
            return datetime.now()

    def _get_task_creation_type(self, task_dir: Path) -> str:
        """Get the creation type of a task from its TOML file.

        Args:
            task_dir: Directory containing the task

        Returns:
            Creation type of the task, or "Unknown" if not found
        """
        try:
            import tomli

            # Find the task TOML file
            toml_files = list(task_dir.glob("task_*.toml"))
            if not toml_files:
                return "Unknown"

            # Use the first TOML file found
            toml_file = toml_files[0]

            with open(toml_file, "rb") as f:
                config = tomli.load(f)

            # Get creation type from metadata section
            metadata: Dict[str, Any] = config.get("metadata", {})
            creation_type: str = metadata.get("creation_type", "Unknown")

            return creation_type

        except Exception:
            # Fallback to Unknown if anything goes wrong
            return "Unknown"
