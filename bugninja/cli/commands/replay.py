"""
Replay command implementation for Bugninja CLI.

This module implements the 'replay' command which replays recorded
browser sessions.
"""

import asyncio
import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from bugninja.api import BugninjaClient, TaskResult

console = Console()


async def replay_session(
    session_file: Optional[Path] = None,
    interactive: bool = False,
) -> TaskResult:
    """Replay a recorded browser session.

    This function replays a previously recorded browser session using the
    `ReplicatorRun` functionality. It automatically finds the latest session
    file if none is specified and provides progress feedback during execution.

    Args:
        session_file: Path to the session file to replay (uses latest if None)
        interactive: Whether to pause after each step for user interaction

    Returns:
        TaskResult containing replay status, metadata, and file paths

    Raises:
        FileNotFoundError: If no session files exist or specified file not found
        ValueError: If session file is not a valid JSON file
        Exception: If session replay fails
    """
    try:
        # Validate input parameters
        if session_file is not None and not session_file.exists():
            raise FileNotFoundError(f"Session file does not exist: {session_file}")

        # Find session file if not provided
        if session_file is None:
            traversal_files = glob.glob("./traversals/*.json")
            if not traversal_files:
                raise FileNotFoundError("No traversal files found in ./traversals/ directory")

            latest_file = max(traversal_files, key=os.path.getctime)
            session_file = Path(latest_file)

        # Validate session file
        if not session_file.exists():
            raise FileNotFoundError(f"Session file does not exist: {session_file}")

        if not session_file.suffix == ".json":
            raise ValueError(f"Session file must be a JSON file: {session_file}")

        console.print(f"🔄 Replaying session: {session_file}")
        console.print(f"   File size: {session_file.stat().st_size} bytes")
        console.print(f"   Created: {datetime.fromtimestamp(session_file.stat().st_mtime)}")
        console.print(f"   Interactive: {interactive}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            replay_progress = progress.add_task("Replaying session...", total=None)

            client = BugninjaClient()
            try:
                result = await client.replay_session(
                    session_file, pause_after_each_step=interactive
                )
                progress.update(replay_progress, completed=True)
                return result
            finally:
                await client.cleanup()

    except Exception as e:
        console.print(f"❌ Session replay failed: {e}")
        raise


app = typer.Typer(name="replay", help="Replay recorded sessions")


@app.command()
def replay(
    session_file: Optional[Path] = typer.Option(
        None, "--session-file", "-f", help="Session file to replay"
    ),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Pause after each step"),
) -> None:
    """Replay a recorded browser session.

    This command replays a previously recorded browser session. If no session
    file is specified, it automatically uses the most recent session file.

    The replay process includes automatic healing capabilities to handle
    failed interactions. Progress is displayed in real-time with detailed
    feedback on success or failure.
    """
    try:
        result = asyncio.run(replay_session(session_file, interactive))

        if result.success:
            console.print("✅ Session replayed successfully!")
            console.print(f"   Execution time: {result.execution_time:.2f} seconds")
            console.print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            console.print(f"❌ Session replay failed: {result.error_message}")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"❌ File not found: {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"❌ Invalid session file: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Session replay error: {e}")
        raise typer.Exit(1)
