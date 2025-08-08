"""
Main Click application for Bugninja CLI.

This module provides the main entry point for the spectacular
Click-based CLI interface.
"""

from typing import Optional

import click

from .themes.colors import echo_info
from .utils.ascii_art import display_banner
from .utils.error_handler import handle_validation_error


@click.group()
@click.version_option(version="0.1.0", prog_name="bugninja")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--output", "-o", type=click.Choice(["human", "json"]), default="human", help="Output format"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, output: str) -> None:
    """🥷 BUGNINJA - AI-Powered Browser Automation Framework

    A spectacular CLI for browser automation with self-healing capabilities.

    Features:
    • Execute browser automation tasks from markdown files
    • Replay recorded sessions with automatic healing
    • Run multiple tasks or sessions in parallel
    • Comprehensive error handling with recovery suggestions
    • Beautiful visual output with progress indicators

    Examples:
        bugninja run task.md                    # Execute single task
        bugninja replay session.json            # Replay single session
        bugninja parallel run task1.md task2.md # Execute multiple tasks
        bugninja list                           # List available sessions
        bugninja status                         # Show system status
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store options in context
    ctx.obj["verbose"] = verbose
    ctx.obj["output"] = output

    # Force color output for better styling
    import os

    os.environ["CLICK_COLORS"] = "1"
    os.environ["FORCE_COLOR"] = "1"
    os.environ["NO_COLOR"] = "0"
    os.environ["TERM"] = "xterm-256color"
    os.environ["COLORTERM"] = "truecolor"

    # Display banner (only for human output)
    if output == "human":
        display_banner()

    # Set up logging if verbose
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)
        echo_info("🔍 Verbose mode enabled")


@cli.command()
@click.argument("task_file", type=click.Path(exists=True))
@click.option("--max-steps", "-m", type=int, help="Override max steps")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with pauses")
@click.option("--headless", is_flag=True, help="Run browser in headless mode")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.option("--retry-on-error", is_flag=True, help="Auto-retry on failure")
@click.pass_context
def run(
    ctx: click.Context,
    task_file: str,
    max_steps: Optional[int],
    interactive: bool,
    headless: bool,
    timeout: Optional[int],
    retry_on_error: bool,
) -> None:
    """🚀 Execute a browser automation task.

    Execute a browser automation task from a markdown file with
    comprehensive error handling and progress feedback.

    Examples:
        bugninja run task.md                    # Basic task execution
        bugninja run task.md --interactive      # Interactive mode
        bugninja run task.md --headless         # Headless execution
        bugninja run task.md --max-steps 50     # Limit steps
    """
    try:
        from .commands.run import execute_task

        # Validate task file
        from .utils.error_handler import validate_task_file

        validate_task_file(task_file)

        # Execute task
        result = execute_task(
            task_file=task_file,
            max_steps=max_steps,
            interactive=interactive,
            headless=headless,
            timeout=timeout,
            retry_on_error=retry_on_error,
            output_format=ctx.obj["output"],
        )

        # Display result
        if ctx.obj["output"] == "human":
            from .utils.display import display_human_task_result

            display_human_task_result(result)
        else:
            from .utils.display import display_json_task_result

            display_json_task_result(result)

        # Exit with error code if failed
        if not result.success:
            ctx.exit(1)

    except Exception as e:
        handle_validation_error(e, "task execution")
        ctx.exit(1)


@cli.command()
@click.argument("session_file", type=click.Path(exists=True))
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with pauses")
@click.option(
    "--enable-healing", is_flag=True, default=True, help="Enable healing for failed actions"
)
@click.option("--pause-after-each-step", is_flag=True, help="Pause after each step")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.pass_context
def replay(
    ctx: click.Context,
    session_file: str,
    interactive: bool,
    enable_healing: bool,
    pause_after_each_step: bool,
    timeout: Optional[int],
) -> None:
    """🔄 Replay a recorded browser session.

    Replay a previously recorded browser session with automatic
    healing capabilities for robust execution.

    Examples:
        bugninja replay session.json                    # Basic replay
        bugninja replay session.json --interactive     # Interactive mode
        bugninja replay session.json --no-healing      # Disable healing
        bugninja replay session.json --pause-steps     # Pause after each step
    """
    try:
        from .commands.replay import execute_replay

        # Validate session file
        from .utils.error_handler import validate_session_file

        validate_session_file(session_file)

        # Execute replay
        result = execute_replay(
            session_file=session_file,
            interactive=interactive,
            enable_healing=enable_healing,
            pause_after_each_step=pause_after_each_step,
            timeout=timeout,
            output_format=ctx.obj["output"],
        )

        # Display result
        if ctx.obj["output"] == "human":
            from .utils.display import display_human_task_result

            display_human_task_result(result)
        else:
            from .utils.display import display_json_task_result

            display_json_task_result(result)

        # Exit with error code if failed
        if not result.success:
            ctx.exit(1)

    except Exception as e:
        handle_validation_error(e, "session replay")
        ctx.exit(1)


@cli.group()
def parallel() -> None:
    """⚡ Execute multiple operations in parallel.

    Run multiple tasks or sessions concurrently for efficient
    bulk processing with comprehensive result aggregation.
    """
    pass


@parallel.command()
@click.argument("task_files", nargs=-1, type=click.Path(exists=True))
@click.option("--workers", "-w", type=int, default=4, help="Number of parallel workers")
@click.option("--continue-on-error", is_flag=True, help="Continue on individual failures")
@click.option("--report", type=click.Path(), help="Generate detailed report")
@click.pass_context
def run_bulk(
    ctx: click.Context,
    task_files: tuple[str, ...],
    workers: int,
    continue_on_error: bool,
    report: Optional[str],
) -> None:
    """🚀 Execute multiple tasks in parallel.

    Execute multiple browser automation tasks concurrently with
    comprehensive result aggregation and error handling.

    Examples:
        bugninja parallel run task1.md task2.md           # Basic parallel execution
        bugninja parallel run *.md --workers 8            # Custom worker count
        bugninja parallel run *.md --continue-on-error    # Continue on failures
    """
    try:
        from .commands.parallel.run import execute_parallel_tasks

        # Validate task files
        from .utils.error_handler import validate_bulk_files

        validate_bulk_files(list(task_files), "task")

        # Execute parallel tasks
        result = execute_parallel_tasks(
            task_files=list(task_files),
            workers=workers,
            continue_on_error=continue_on_error,
            report_file=report,
            output_format=ctx.obj["output"],
        )

        # Display result
        if ctx.obj["output"] == "human":
            from .utils.display import display_human_bulk_result

            display_human_bulk_result(result)
        else:
            from .utils.display import display_json_bulk_result

            display_json_bulk_result(result)

        # Exit with error code if failed
        if not result.overall_success:
            ctx.exit(1)

    except Exception as e:
        handle_validation_error(e, "parallel task execution")
        ctx.exit(1)


@parallel.command()
@click.argument("session_files", nargs=-1, type=click.Path(exists=True))
@click.option("--workers", "-w", type=int, default=4, help="Number of parallel workers")
@click.option(
    "--enable-healing", is_flag=True, default=True, help="Enable healing for failed actions"
)
@click.option("--pause-after-each-step", is_flag=True, help="Pause after each step")
@click.option("--continue-on-error", is_flag=True, help="Continue on individual failures")
@click.pass_context
def replay_bulk(
    ctx: click.Context,
    session_files: tuple[str, ...],
    workers: int,
    enable_healing: bool,
    pause_after_each_step: bool,
    continue_on_error: bool,
) -> None:
    """🔄 Replay multiple sessions in parallel.

    Replay multiple recorded browser sessions concurrently with
    automatic healing and comprehensive result aggregation.

    Examples:
        bugninja parallel replay session1.json session2.json    # Basic parallel replay
        bugninja parallel replay *.json --workers 8            # Custom worker count
        bugninja parallel replay *.json --no-healing           # Disable healing
    """
    try:
        from .commands.parallel.replay import execute_parallel_replays

        # Validate session files
        from .utils.error_handler import validate_bulk_files

        validate_bulk_files(list(session_files), "session")

        # Execute parallel replays
        result = execute_parallel_replays(
            session_files=list(session_files),
            workers=workers,
            enable_healing=enable_healing,
            pause_after_each_step=pause_after_each_step,
            continue_on_error=continue_on_error,
            output_format=ctx.obj["output"],
        )

        # Display result
        if ctx.obj["output"] == "human":
            from .utils.display import display_human_bulk_result

            display_human_bulk_result(result)
        else:
            from .utils.display import display_json_bulk_result

            display_json_bulk_result(result)

        # Exit with error code if failed
        if not result.overall_success:
            ctx.exit(1)

    except Exception as e:
        handle_validation_error(e, "parallel session replay")
        ctx.exit(1)


@cli.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.pass_context
def list(ctx: click.Context, detailed: bool) -> None:
    """📋 List available browser sessions.

    Display all available recorded browser sessions with
    metadata and file information.

    Examples:
        bugninja list                    # Basic session listing
        bugninja list --detailed        # Detailed information
    """
    try:
        from .commands.list import list_sessions

        sessions = list_sessions(detailed=detailed)

        if ctx.obj["output"] == "human":
            from .utils.display import display_list_sessions

            display_list_sessions(sessions)
        else:
            import json

            click.echo(json.dumps(sessions, indent=2))

    except Exception as e:
        handle_validation_error(e, "session listing")
        ctx.exit(1)


@cli.command()
@click.option("--run-id", "-r", help="Specific run ID to show status for")
@click.pass_context
def status(ctx: click.Context, run_id: Optional[str]) -> None:
    """📊 Show system and run status.

    Display current system status, available resources,
    and specific run information if provided.

    Examples:
        bugninja status                    # System status
        bugninja status --run-id abc123    # Specific run status
    """
    try:
        from .commands.status import show_status

        status_data = show_status(run_id=run_id)

        if ctx.obj["output"] == "human":
            from .utils.display import display_status_summary

            display_status_summary(status_data)
        else:
            import json

            click.echo(json.dumps(status_data, indent=2))

    except Exception as e:
        handle_validation_error(e, "status check")
        ctx.exit(1)


@cli.command()
@click.option("--fix", is_flag=True, help="Attempt to fix detected issues")
@click.pass_context
def doctor(ctx: click.Context, fix: bool) -> None:
    """🏥 System health check and diagnostics.

    Perform comprehensive system health checks including
    browser installation, API connectivity, and configuration.

    Examples:
        bugninja doctor           # Basic health check
        bugninja doctor --fix     # Attempt to fix issues
    """
    try:
        from .commands.doctor import run_health_check

        results = run_health_check(fix=fix)

        if ctx.obj["output"] == "human":
            from .utils.display import display_health_results

            display_health_results(results)
        else:
            import json

            click.echo(json.dumps(results, indent=2))

    except Exception as e:
        handle_validation_error(e, "health check")
        ctx.exit(1)


if __name__ == "__main__":
    cli()
