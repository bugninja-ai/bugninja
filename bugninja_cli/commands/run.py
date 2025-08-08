"""
Run command implementation for Bugninja CLI.

This module implements the 'run' command for executing
browser automation tasks.
"""

import asyncio
from typing import Optional

import click

from bugninja.api import BugninjaClient, BugninjaTaskResult, Task

from ..themes.colors import echo_info
from ..utils.ascii_art import display_progress, get_operation_icon


async def execute_task_async(
    task_file: str,
    max_steps: Optional[int] = None,
    interactive: bool = False,
    headless: bool = False,
    timeout: Optional[int] = None,
    retry_on_error: bool = False,
    output_format: str = "human",
) -> BugninjaTaskResult:
    """Execute a browser automation task asynchronously.

    Args:
        task_file: Path to the task markdown file
        max_steps: Optional override for max steps
        interactive: Whether to enable interactive mode
        headless: Whether to run in headless mode
        timeout: Execution timeout in seconds
        retry_on_error: Whether to retry on error
        output_format: Output format ('human' or 'json')

    Returns:
        BugninjaTaskResult containing execution results
    """
    try:
        # Parse and validate task file
        if output_format == "human":
            echo_info(f"📄 Parsing task file: {task_file}")

        # TODO: Implement proper task parsing
        # For now, create a basic task from file content
        with open(task_file, "r") as f:
            task_content = f.read()

        # Create task object
        task = Task(
            description=task_content[:200] + "..." if len(task_content) > 200 else task_content,
            max_steps=max_steps or 50,
            enable_healing=True,
            allowed_domains=[],
            secrets={},
        )

        # Display task information
        if output_format == "human":
            operation_icon = get_operation_icon("run")
            echo_info(f"{operation_icon} Starting task execution...")
            click.echo(
                f"   Description: {task.description[:100]}{'...' if len(task.description) > 100 else ''}"
            )
            click.echo(f"   Max Steps: {task.max_steps}")
            click.echo(f"   Headless: {'Yes' if headless else 'No'}")
            click.echo(f"   Interactive: {'Yes' if interactive else 'No'}")
            if task.allowed_domains:
                click.echo(f"   Allowed Domains: {', '.join(task.allowed_domains)}")

        # Create client with configuration
        client_config = None
        if headless:
            from bugninja.api.models import BugninjaConfig

            client_config = BugninjaConfig(headless=True)

        # Execute task
        client = BugninjaClient(config=client_config)

        try:
            if output_format == "human":
                display_progress(0, task.max_steps, "Executing task...")

            result = await client.run_task(task)

            if output_format == "human":
                display_progress(task.max_steps, task.max_steps, "Task completed!")

            return result

        finally:
            await client.cleanup()

    except Exception as e:
        # Create error result
        from bugninja.api.models import (
            BugninjaErrorType,
            BugninjaTaskError,
            BugninjaTaskResult,
            HealingStatus,
            OperationType,
        )

        error_result = BugninjaTaskResult(
            success=False,
            operation_type=OperationType.FIRST_TRAVERSAL,
            healing_status=HealingStatus.NONE,
            execution_time=0.0,
            steps_completed=0,
            total_steps=task.max_steps if "task" in locals() else 0,
            error=BugninjaTaskError(
                error_type=BugninjaErrorType.TASK_EXECUTION_ERROR,
                message=str(e),
                details={"task_file": task_file},
                original_error=f"{type(e).__name__}: {str(e)}",
                suggested_action="Check task file format and try again",
            ),
            metadata={"task_file": task_file},
        )

        return error_result


def execute_task(
    task_file: str,
    max_steps: Optional[int] = None,
    interactive: bool = False,
    headless: bool = False,
    timeout: Optional[int] = None,
    retry_on_error: bool = False,
    output_format: str = "human",
) -> BugninjaTaskResult:
    """Execute a browser automation task.

    Args:
        task_file: Path to the task markdown file
        max_steps: Optional override for max steps
        interactive: Whether to enable interactive mode
        headless: Whether to run in headless mode
        timeout: Execution timeout in seconds
        retry_on_error: Whether to retry on error
        output_format: Output format ('human' or 'json')

    Returns:
        BugninjaTaskResult containing execution results
    """
    try:
        return asyncio.run(
            execute_task_async(
                task_file=task_file,
                max_steps=max_steps,
                interactive=interactive,
                headless=headless,
                timeout=timeout,
                retry_on_error=retry_on_error,
                output_format=output_format,
            )
        )
    except Exception as e:
        # Handle any remaining exceptions
        from bugninja.api.models import (
            BugninjaErrorType,
            BugninjaTaskError,
            BugninjaTaskResult,
            HealingStatus,
            OperationType,
        )

        return BugninjaTaskResult(
            success=False,
            operation_type=OperationType.FIRST_TRAVERSAL,
            healing_status=HealingStatus.NONE,
            execution_time=0.0,
            steps_completed=0,
            total_steps=0,
            error=BugninjaTaskError(
                error_type=BugninjaErrorType.TASK_EXECUTION_ERROR,
                message=str(e),
                details={"task_file": task_file},
                original_error=f"{type(e).__name__}: {str(e)}",
                suggested_action="Check system configuration and try again",
            ),
            metadata={"task_file": task_file},
        )
