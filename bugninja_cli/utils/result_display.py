"""
Result display utilities for Bugninja CLI.

This module provides utilities for displaying task execution results
and error messages in a consistent, formatted manner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from bugninja.schemas import TaskExecutionResult, TaskInfo

console = Console()


def display_task_success(task_info: TaskInfo, result: TaskExecutionResult) -> None:
    """Display successful task execution result.

    Args:
        task_info: Task information
        result: Execution result
    """
    success_text = (
        f"✅ Task '{task_info.name}' completed successfully!\n\n"
        f"⏱️ Execution time: {result.execution_time:.2f} seconds\n"
        f"📁 Traversal saved: {result.traversal_path}"
        if result.traversal_path
        else "📁 No traversal file generated"
    )

    console.print(
        Panel(
            Text(success_text, style="green"),
            title="Task Completed",
            border_style="green",
        )
    )


def display_task_failure(task_info: TaskInfo, result: TaskExecutionResult) -> None:
    """Display failed task execution result.

    Args:
        task_info: Task information
        result: Execution result
    """
    error_text = (
        f"❌ Task '{task_info.name}' failed!\n\n"
        f"⏱️ Execution time: {result.execution_time:.2f} seconds\n"
        f"🚨 Error:\n" + result.error_message
        if result.error_message
        else "No error message available"
    )

    console.print(
        Panel(
            Text(error_text, style="red"),
            title="Task Failed",
            border_style="red",
        )
    )


def display_execution_error(task_info: TaskInfo, error: Exception) -> None:
    """Display task execution error.

    Args:
        task_info: Task information
        error: Exception that occurred
    """
    console.print(
        Panel(
            Text(f"❌ Failed to execute task '{task_info.name}': {error}", style="red"),
            title="Execution Error",
            border_style="red",
        )
    )


def display_task_not_found(task_identifier: str, available_tasks: str) -> None:
    """Display task not found error with available tasks.

    Args:
        task_identifier: The identifier that was not found
        available_tasks: Formatted list of available tasks
    """
    console.print(
        Panel(
            Text(
                f"❌ Task '{task_identifier}' not found.\n\n"
                f"Available tasks:\n{available_tasks}",
                style="red",
            ),
            title="Task Not Found",
            border_style="red",
        )
    )
