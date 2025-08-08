"""
Replay command implementation for Bugninja CLI.

This module implements the 'replay' command for replaying
recorded browser sessions.
"""

import asyncio
from pathlib import Path
from typing import Optional

import click

from bugninja.api import BugninjaClient, BugninjaTaskResult

from ..themes.colors import echo_info
from ..utils.ascii_art import display_progress, get_operation_icon


async def execute_replay_async(
    session_file: str,
    interactive: bool = False,
    enable_healing: bool = True,
    pause_after_each_step: bool = False,
    timeout: Optional[int] = None,
    output_format: str = "human",
) -> BugninjaTaskResult:
    """Execute a session replay asynchronously.

    Args:
        session_file: Path to the session JSON file
        interactive: Whether to enable interactive mode
        enable_healing: Whether to enable healing for failed actions
        pause_after_each_step: Whether to pause after each step
        timeout: Execution timeout in seconds
        output_format: Output format ('human' or 'json')

    Returns:
        BugninjaTaskResult containing replay results
    """
    try:
        # Display session information
        if output_format == "human":
            operation_icon = get_operation_icon("replay")
            echo_info(f"{operation_icon} Starting session replay...")
            click.echo(f"   Session File: {session_file}")
            click.echo(f"   Interactive: {'Yes' if interactive else 'No'}")
            click.echo(f"   Healing Enabled: {'Yes' if enable_healing else 'No'}")
            click.echo(f"   Pause After Steps: {'Yes' if pause_after_each_step else 'No'}")

            # Display file information
            session_path = Path(session_file)
            if session_path.exists():
                file_size = session_path.stat().st_size
                click.echo(f"   File Size: {file_size:,} bytes")

        # Execute replay
        client = BugninjaClient()

        try:
            if output_format == "human":
                display_progress(0, 100, "Replaying session...")

            result = await client.replay_session(
                session_file=Path(session_file),
                pause_after_each_step=pause_after_each_step,
                enable_healing=enable_healing,
            )

            if output_format == "human":
                display_progress(100, 100, "Session replay completed!")

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
            operation_type=OperationType.REPLAY,
            healing_status=HealingStatus.NONE,
            execution_time=0.0,
            steps_completed=0,
            total_steps=0,
            traversal_file=Path(session_file),
            error=BugninjaTaskError(
                error_type=BugninjaErrorType.SESSION_REPLAY_ERROR,
                message=str(e),
                details={"session_file": session_file},
                original_error=f"{type(e).__name__}: {str(e)}",
                suggested_action="Check session file format and try again",
            ),
            metadata={"session_file": session_file},
        )

        return error_result


def execute_replay(
    session_file: str,
    interactive: bool = False,
    enable_healing: bool = True,
    pause_after_each_step: bool = False,
    timeout: Optional[int] = None,
    output_format: str = "human",
) -> BugninjaTaskResult:
    """Execute a session replay.

    Args:
        session_file: Path to the session JSON file
        interactive: Whether to enable interactive mode
        enable_healing: Whether to enable healing for failed actions
        pause_after_each_step: Whether to pause after each step
        timeout: Execution timeout in seconds
        output_format: Output format ('human' or 'json')

    Returns:
        BugninjaTaskResult containing replay results
    """
    try:
        return asyncio.run(
            execute_replay_async(
                session_file=session_file,
                interactive=interactive,
                enable_healing=enable_healing,
                pause_after_each_step=pause_after_each_step,
                timeout=timeout,
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
            operation_type=OperationType.REPLAY,
            healing_status=HealingStatus.NONE,
            execution_time=0.0,
            steps_completed=0,
            total_steps=0,
            traversal_file=Path(session_file),
            error=BugninjaTaskError(
                error_type=BugninjaErrorType.SESSION_REPLAY_ERROR,
                message=str(e),
                details={"session_file": session_file},
                original_error=f"{type(e).__name__}: {str(e)}",
                suggested_action="Check system configuration and try again",
            ),
            metadata={"session_file": session_file},
        )
