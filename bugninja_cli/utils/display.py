"""
Display utilities for Bugninja CLI.

This module provides utilities for displaying results in both
human-focused and JSON formats.
"""

import json
from typing import Any, Dict, List, Optional

import click

from bugninja.api.models import (
    BugninjaTaskError,
    BugninjaTaskResult,
    BulkBugninjaTaskResult,
    HealingStatus,
)

from ..themes.colors import (
    BugninjaColors,
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
)
from .ascii_art import display_separator, get_status_icon


def display_human_task_result(result: BugninjaTaskResult) -> None:
    """Display task result in human-friendly format.

    Args:
        result: Task result to display
    """
    if result.success:
        echo_success("✅ Task completed successfully!", bold=True)
        click.echo(f"   Operation: {result.operation_type.value}")
        click.echo(f"   Steps: {result.steps_completed}/{result.total_steps}")
        click.echo(f"   Time: {result.execution_time:.2f}s")

        # Display healing status
        healing_icon = (
            get_status_icon("healing") if result.healing_status == HealingStatus.USED else "⚪"
        )
        click.echo(f"   Healing: {healing_icon} {result.healing_status.value}")

        # Display file information
        if result.traversal_file:
            click.echo(f"   File: {result.traversal_file}")
        if result.screenshots_dir:
            click.echo(f"   Screenshots: {result.screenshots_dir}")

        # Display metadata if available
        if result.metadata:
            click.echo("   Metadata:")
            for key, value in result.metadata.items():
                click.echo(f"     {key}: {value}")
    else:
        echo_error("❌ Task failed!", bold=True)
        if result.error:
            display_error_with_suggestions(result.error)


def display_human_bulk_result(result: BulkBugninjaTaskResult) -> None:
    """Display bulk result in human-friendly format.

    Args:
        result: Bulk result to display
    """
    # Overall summary
    overall_icon = (
        get_status_icon("success") if result.overall_success else get_status_icon("error")
    )
    click.echo(f"\n{overall_icon} Bulk Operation Summary")
    display_separator()

    click.echo(f"   Overall Success: {overall_icon} {'Yes' if result.overall_success else 'No'}")
    click.echo(f"   Total Tasks: {result.total_tasks}")
    click.echo(f"   Successful: {result.successful_tasks}")
    click.echo(f"   Failed: {result.failed_tasks}")
    click.echo(f"   Total Time: {result.total_execution_time:.2f}s")

    # Error summary if available
    if result.error_summary:
        click.echo("   Error Summary:")
        for error_type, count in result.error_summary.items():
            error_icon = get_status_icon("error")
            click.echo(f"     {error_icon} {error_type.value}: {count}")

    # Individual results
    if result.individual_results:
        click.echo("\n📋 Individual Results:")
        for i, individual_result in enumerate(result.individual_results, 1):
            status_icon = (
                get_status_icon("success")
                if individual_result.success
                else get_status_icon("error")
            )
            click.echo(
                f"   Task {i}: {status_icon} {'Success' if individual_result.success else 'Failed'}"
            )

            if not individual_result.success and individual_result.error:
                click.echo(f"     Error: {individual_result.error.message}")
                click.echo(f"     Type: {individual_result.error.error_type.value}")


def display_json_task_result(result: BugninjaTaskResult) -> None:
    """Display task result in JSON format.

    Args:
        result: Task result to display
    """
    json_output = {
        "success": result.success,
        "operation_type": result.operation_type.value,
        "healing_status": result.healing_status.value,
        "execution_time": result.execution_time,
        "steps_completed": result.steps_completed,
        "total_steps": result.total_steps,
        "traversal_file": str(result.traversal_file) if result.traversal_file else None,
        "screenshots_dir": str(result.screenshots_dir) if result.screenshots_dir else None,
        "error": result.error.dict() if result.error else None,
        "metadata": result.metadata,
    }
    click.echo(json.dumps(json_output, indent=2))


def display_json_bulk_result(result: BulkBugninjaTaskResult) -> None:
    """Display bulk result in JSON format.

    Args:
        result: Bulk result to display
    """
    json_output = {
        "overall_success": result.overall_success,
        "total_tasks": result.total_tasks,
        "successful_tasks": result.successful_tasks,
        "failed_tasks": result.failed_tasks,
        "total_execution_time": result.total_execution_time,
        "individual_results": [r.dict() for r in result.individual_results],
        "error_summary": (
            {k.value: v for k, v in result.error_summary.items()} if result.error_summary else None
        ),
        "metadata": result.metadata,
    }
    click.echo(json.dumps(json_output, indent=2))


def display_error_with_suggestions(error: BugninjaTaskError) -> None:
    """Display error with suggestions for recovery.

    Args:
        error: Error object to display
    """
    echo_error(f"   Error: {error.message}")
    click.echo(f"   Type: {error.error_type.value}")

    if error.suggested_action:
        echo_info(f"   Suggestion: {error.suggested_action}")

    if error.details:
        click.echo("   Details:")
        for key, value in error.details.items():
            click.echo(f"     {key}: {value}")

    if error.original_error:
        click.echo(f"   Original: {error.original_error}")


def display_progress(current: int, total: int, description: str = "") -> None:
    """Display progress bar with description.

    Args:
        current: Current progress value
        total: Total value
        description: Description of the operation
    """
    from .ascii_art import get_progress_bar

    progress_bar = get_progress_bar(current, total)
    if description:
        click.echo(f"{description} {progress_bar}")
    else:
        click.echo(progress_bar)


def display_table(headers: List[str], rows: List[List[str]], title: Optional[str] = None) -> None:
    """Display data in a formatted table.

    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of values)
        title: Optional table title
    """
    if title:
        styled_title = BugninjaColors.primary(title, bold=True)
        click.echo(f"\n{styled_title}")

    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width)

    # Create separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    styled_separator = BugninjaColors.muted(separator)

    # Display table
    click.echo(styled_separator)

    # Headers
    header_row = "|"
    for header, width in zip(headers, col_widths):
        styled_header = BugninjaColors.primary(header, bold=True)
        header_row += f" {styled_header:<{width}} |"
    click.echo(header_row)

    click.echo(styled_separator)

    # Data rows
    for row in rows:
        data_row = "|"
        for i, (value, width) in enumerate(zip(row, col_widths)):
            data_row += f" {str(value):<{width}} |"
        click.echo(data_row)

    click.echo(styled_separator)


def display_list_sessions(sessions: List[Dict[str, Any]]) -> None:
    """Display list of sessions in table format.

    Args:
        sessions: List of session dictionaries
    """
    if not sessions:
        echo_warning("📋 No sessions found. Run a task first to create sessions.")
        return

    headers = ["Name", "Created", "Size", "Steps"]
    rows = []

    for session in sessions:
        rows.append(
            [
                session.get("name", "Unknown"),
                session.get("created", "Unknown"),
                session.get("size", "Unknown"),
                str(session.get("steps", 0)),
            ]
        )

    display_table(headers, rows, "Available Sessions")


def display_status_summary(status_data: Dict[str, Any]) -> None:
    """Display status summary information.

    Args:
        status_data: Status data dictionary
    """
    echo_info("📊 Status Summary", bold=True)
    display_separator()

    for key, value in status_data.items():
        if isinstance(value, bool):
            icon = get_status_icon("success") if value else get_status_icon("error")
            status = "Available" if value else "Unavailable"
            click.echo(f"   {key}: {icon} {status}")
        else:
            click.echo(f"   {key}: {value}")


def display_health_results(results: Dict[str, Any]) -> None:
    """Display health check results.

    Args:
        results: Health check results dictionary
    """
    echo_info("🏥 Health Check Results", bold=True)
    display_separator()

    for check_name, check_data in results.items():
        status = check_data.get("status", "unknown")
        message = check_data.get("message", "No message")
        fixable = check_data.get("fixable", False)

        if status == "healthy":
            icon = get_status_icon("success")
        elif status == "warning":
            icon = get_status_icon("warning")
        elif status == "error":
            icon = get_status_icon("error")
        else:
            icon = "•"

        click.echo(f"   {check_name}: {icon} {message}")
        if fixable:
            click.echo("     (Fixable)")
