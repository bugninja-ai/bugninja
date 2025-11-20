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

        # Create Jira ticket if replay failed (non-blocking)
        if not result.success:
            _create_jira_ticket_for_replay_failure(
                task_toml_path, result, traversal_path, history_manager
            )

    except Exception as e:
        raise ValueError(f"Failed to update task metadata: {e}")


def _create_jira_ticket_for_replay_failure(
    task_toml_path: Path,
    result: TaskExecutionResult,
    traversal_path: Path,
    history_manager: RunHistoryManager,
) -> None:
    """Create Jira ticket for failed replay (non-blocking).

    Args:
        task_toml_path (Path): Path to task TOML file
        result (TaskExecutionResult): Replay execution result
        traversal_path (Path): Path to original traversal file
        history_manager (RunHistoryManager): Run history manager instance
    """
    try:
        import tomli

        from bugninja.schemas import TaskInfo
        from bugninja_cli.utils.jira_integration import JiraIntegration

        # Get task info from TOML file
        task_dir = task_toml_path.parent
        with open(task_toml_path, "rb") as f:
            config = tomli.load(f)

        task_section = config.get("task", {})
        metadata_section = config.get("metadata", {})
        task_info = TaskInfo(
            name=task_section.get("name", "Unknown"),
            task_id=metadata_section.get("task_id", "Unknown"),
            folder_name=task_dir.name,
            task_path=task_dir,
            toml_path=task_toml_path,
        )

        # Use shared helper function
        JiraIntegration.create_ticket_for_task_failure(
            task_info=task_info,
            result=result,
            run_type="replay",
            history_manager=history_manager,
            traversal_path_override=result.traversal_path or traversal_path,
        )

    except Exception as e:
        # Log error but don't block execution
        from bugninja.utils.logging_config import logger

        logger.error(f"Failed to create Jira ticket for replay failure: {str(e)}")
