"""
Task lookup and display utilities for Bugninja CLI.

This module provides utilities for finding tasks by various identifiers
and displaying task-related information in a consistent manner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from bugninja_cli.utils.task_manager import TaskManager

if TYPE_CHECKING:
    from bugninja.schemas import TaskInfo


def get_task_by_identifier(task_manager: TaskManager, identifier: str) -> Optional[TaskInfo]:
    """Get task by folder name or CUID.

    Args:
        task_manager (TaskManager): Task manager instance
        identifier (str): Task identifier (folder name or CUID)

    Returns:
        TaskInfo: Task information if found, None otherwise
    """
    # First try folder name lookup
    task: Optional[TaskInfo] = task_manager.get_task_by_name(identifier)
    if task:
        return task

    # Then try CUID lookup
    task = task_manager.get_task_by_cuid(identifier)
    if task:
        return task

    return None


def get_available_tasks_list(task_manager: TaskManager) -> str:
    """Get a formatted list of available tasks.

    Args:
        task_manager: Task manager instance

    Returns:
        str: Formatted string of available tasks
    """
    tasks = task_manager.list_tasks()
    return "\n".join([f"  • {task.name} ({task.folder_name})" for task in tasks])
