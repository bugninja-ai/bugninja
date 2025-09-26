"""
Replay metadata management utilities for Bugninja CLI.

This module provides utilities for managing replay run metadata in JSON files,
including creating replay run entries and updating task metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bugninja_cli.utils.run_history_manager import RunHistoryManager

if TYPE_CHECKING:
    from bugninja.schemas import TaskExecutionResult


def extract_original_traversal_id(traversal_path: Path) -> str:
    """Extract the original traversal ID from the traversal filename.

    Args:
        traversal_path: Path to the traversal file

    Returns:
        str: The original traversal ID (last part after underscore)
    """
    return traversal_path.stem.split("_")[-1]


def update_task_metadata_with_replay(
    task_toml_path: Path,
    traversal_path: Path,
    result: TaskExecutionResult,
    healing_enabled: bool,
) -> None:
    """Update task metadata with replay run information.

    Args:
        task_toml_path: Path to the task TOML file
        traversal_path: Path to the original traversal file
        result: The replay execution result
        healing_enabled: Whether healing was enabled during replay

    Raises:
        ValueError: If run history cannot be updated
    """
    try:
        # Get task directory from TOML path
        task_dir = task_toml_path.parent

        # Extract original traversal ID
        original_traversal_id = extract_original_traversal_id(traversal_path)

        # Use RunHistoryManager to add the replay run
        history_manager = RunHistoryManager(task_dir)
        history_manager.add_replay_run(result, original_traversal_id, healing_enabled)

    except Exception as e:
        raise ValueError(f"Failed to update task metadata: {e}")
