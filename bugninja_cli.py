#!/usr/bin/env python3
"""
Bugninja CLI entry point.

This script provides the command-line interface for the Bugninja
browser automation framework.
"""

import typer
from rich.console import Console

from bugninja.cli.commands import heal, list_cmd, replay, run

console = Console()

app = typer.Typer(
    name="bugninja",
    help="AI-Powered Browser Automation & Self-Healing Framework",
    add_completion=False,
    rich_markup_mode="rich",
)

# Add commands
app.add_typer(run, name="run", help="Execute browser automation tasks")
app.add_typer(replay, name="replay", help="Replay recorded sessions")
app.add_typer(heal, name="heal", help="Heal failed sessions")
app.add_typer(list_cmd, name="list", help="List available sessions")


@app.callback()
def main() -> None:
    """Bugninja - AI-Powered Browser Automation & Self-Healing Framework.

    This CLI provides a comprehensive interface for browser automation tasks.
    It supports markdown-based task definitions, session replay with healing,
    and session management capabilities.

    Key Features:
    - Execute browser automation tasks from markdown files
    - Replay recorded sessions with automatic healing
    - Heal failed sessions using AI-powered recovery
    - List and manage available sessions
    - Environment variable support for secure credential management

    For detailed help on specific commands, use: bugninja <command> --help
    """
    pass


if __name__ == "__main__":
    app()
