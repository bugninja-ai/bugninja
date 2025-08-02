"""
List command implementation for Bugninja CLI.

This module implements the 'list' command which lists available
browser sessions.
"""

import asyncio
from typing import List

import typer
from rich.console import Console
from rich.table import Table

from bugninja.api import BugninjaClient, SessionInfo

console = Console()


async def list_sessions() -> List[SessionInfo]:
    """List all available browser sessions.

    This function retrieves all available session files from the traversals
    directory and creates `SessionInfo` objects with metadata for each session.
    It handles file parsing errors gracefully and returns an empty list if
    no sessions are found.

    Returns:
        List of SessionInfo objects containing session metadata including
        file path, creation time, file size, and step count

    Raises:
        Exception: If session listing fails due to file system issues
    """
    try:
        client = BugninjaClient()
        try:
            sessions = client.list_sessions()
            return sessions
        finally:
            await client.cleanup()

    except Exception as e:
        console.print(f"❌ Failed to list sessions: {e}")
        raise


app = typer.Typer(name="list", help="List available sessions")


@app.command()
def list_cmd() -> None:
    """List all available browser sessions.

    This command displays all available browser sessions in a formatted table.
    The table includes session name, creation date, file size, and step count.
    Sessions are sorted by creation time with the most recent first.

    If no sessions are found, a helpful message is displayed indicating
    that tasks need to be run first to create sessions.
    """
    try:
        sessions = asyncio.run(list_sessions())

        if not sessions:
            console.print("📋 No sessions found. Run a task first to create sessions.")
            return

        console.print(f"📋 Found {len(sessions)} sessions:")

        # Create table
        table = Table(title="Available Sessions")
        table.add_column("Name", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Size", style="yellow")
        table.add_column("Steps", style="blue")

        for session in sessions:
            table.add_row(
                session.file_path.name,
                session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                f"{session.file_path.stat().st_size:,} bytes",
                str(session.steps_count),
            )

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"❌ Directory not found: {e}")
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(f"❌ Permission denied: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error listing sessions: {e}")
        raise typer.Exit(1)
