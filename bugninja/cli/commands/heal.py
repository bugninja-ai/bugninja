"""
Heal command implementation for Bugninja CLI.

This module implements the 'heal' command which heals failed
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


async def heal_session(
    session_file: Optional[Path] = None,
    interactive: bool = False,
) -> TaskResult:
    """Heal a failed browser session.

    This function attempts to heal a failed browser session by using the
    `HealerAgent` to recover from errors. It automatically finds the latest
    session file if none is specified and provides progress feedback.

    Args:
        session_file: Path to the session file to heal (uses latest if None)
        interactive: Whether to pause after each step for user interaction

    Returns:
        TaskResult containing healing status, metadata, and file paths

    Raises:
        FileNotFoundError: If no session files exist or specified file not found
        ValueError: If session file is not a valid JSON file
        Exception: If session healing fails
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

        console.print(f"🩹 Healing session: {session_file}")
        console.print(f"   File size: {session_file.stat().st_size} bytes")
        console.print(f"   Created: {datetime.fromtimestamp(session_file.stat().st_mtime)}")
        console.print(f"   Interactive: {interactive}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            heal_progress = progress.add_task("Healing session...", total=None)

            client = BugninjaClient()
            try:
                result = await client.heal_session(session_file, pause_after_each_step=interactive)
                progress.update(heal_progress, completed=True)
                return result
            finally:
                await client.cleanup()

    except Exception as e:
        console.print(f"❌ Session healing failed: {e}")
        raise


app = typer.Typer(name="heal", help="Heal failed sessions")


@app.command()
def heal(
    session_file: Optional[Path] = typer.Option(
        None, "--session-file", "-f", help="Session file to heal"
    ),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Pause after each step"),
) -> None:
    """Heal a failed browser session.

    This command attempts to heal a failed browser session by using the
    `HealerAgent` to recover from errors. If no session file is specified,
    it automatically uses the most recent session file.

    The healing process uses AI-powered recovery mechanisms to fix failed
    interactions and complete the original task. Progress is displayed in
    real-time with detailed feedback on success or failure.
    """
    try:
        result = asyncio.run(heal_session(session_file, interactive))

        if result.success:
            console.print("✅ Session healed successfully!")
            console.print(f"   Execution time: {result.execution_time:.2f} seconds")
            console.print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            console.print(f"❌ Session healing failed: {result.error_message}")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"❌ File not found: {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"❌ Invalid session file: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Session healing error: {e}")
        raise typer.Exit(1)
