"""
Run command implementation for Bugninja CLI.

This module implements the 'run' command which executes browser automation
tasks from markdown files.
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from bugninja.api import BugninjaClient, Task, TaskResult
from bugninja.cli.parser import parse_task_markdown, validate_task_config
from bugninja.config import ConfigurationFactory, Environment

console = Console()


async def run_task(
    task_file: Path,
    max_steps: Optional[int] = None,
    interactive: bool = False,
) -> TaskResult:
    """Execute a browser automation task from a markdown file.

    This function parses a markdown task file, validates the configuration,
    creates a `Task` object, and executes it using the `BugninjaClient`.
    It provides progress feedback and handles cleanup automatically.

    Args:
        task_file: Path to the markdown task file containing task definition
        max_steps: Optional override for maximum steps (overrides file setting)
        interactive: Whether to enable interactive mode with pauses

    Returns:
        TaskResult containing execution status, metadata, and file paths

    Raises:
        ValueError: If task file is invalid or configuration is incorrect
        FileNotFoundError: If task file does not exist
        Exception: If task execution fails
    """
    try:
        # Validate input parameters
        if not task_file.exists():
            raise FileNotFoundError(f"Task file does not exist: {task_file}")

        if max_steps is not None and (max_steps <= 0 or max_steps > 1000):
            raise ValueError(f"Max steps must be between 1 and 1000, got: {max_steps}")

        # Parse and validate task file
        console.print(f"📄 Parsing task file: {task_file}")
        config = parse_task_markdown(task_file)
        validate_task_config(config)

        # Override max_steps if provided
        if max_steps is not None:
            config["max_steps"] = max_steps

        # Create task object
        task = Task(
            description=config["description"],
            target_url=config["target_url"],
            max_steps=config["max_steps"],
            enable_healing=True,
            allowed_domains=config["allowed_domains"],
            secrets=config["secrets"],
        )

        # Get authentication prompt from settings
        settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)
        if settings.authentication_handling_prompt:
            task.extend_planner_system_message = settings.authentication_handling_prompt

        # Execute task
        console.print("🚀 Starting task execution...")
        console.print(
            f"   Description: {task.description[:100]}{'...' if len(task.description) > 100 else ''}"
        )
        console.print(f"   Max Steps: {task.max_steps}")
        console.print(
            f"   Allowed Domains: {', '.join(task.allowed_domains) if task.allowed_domains else 'None'}"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task_progress = progress.add_task("Executing task...", total=None)

            client = BugninjaClient()
            try:
                result = await client.run_task(task)
                progress.update(task_progress, completed=True)
                return result
            finally:
                await client.cleanup()

    except Exception as e:
        console.print(f"❌ Task execution failed: {e}")
        raise


app = typer.Typer(name="run", help="Execute browser automation tasks")


@app.command()
def run(
    task_file: Path = typer.Argument(..., help="Markdown file containing task definition"),
    max_steps: Optional[int] = typer.Option(None, "--max-steps", "-m", help="Override max steps"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
) -> None:
    """Execute a browser automation task from a markdown file.

    This command parses a markdown task file and executes the defined browser
    automation task. The task file should contain a description, configuration
    settings, and optional secrets for authentication.

    The command provides real-time progress feedback and automatically handles
    resource cleanup. If the task fails, detailed error information is displayed.
    """
    try:
        result = asyncio.run(run_task(task_file, max_steps, interactive))

        if result.success:
            console.print("✅ Task completed successfully!")
            console.print(f"   Steps completed: {result.steps_completed}")
            console.print(f"   Execution time: {result.execution_time:.2f} seconds")
            console.print(f"   Traversal file: {result.traversal_file}")
            console.print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            console.print(f"❌ Task failed: {result.error_message}")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"❌ File not found: {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"❌ Invalid configuration: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Task execution error: {e}")
        raise typer.Exit(1)
