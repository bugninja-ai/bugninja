"""
Main CLI entry point for Bugninja.

This module provides the command-line interface for the Bugninja
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
app.add_typer(run.app, name="run", help="Execute browser automation tasks")
app.add_typer(replay.app, name="replay", help="Replay recorded sessions")
app.add_typer(heal.app, name="heal", help="Heal failed sessions")
app.add_typer(list_cmd.app, name="list", help="List available sessions")


@app.callback()
def main() -> None:
    """Bugninja - AI-Powered Browser Automation & Self-Healing Framework.

    This CLI provides commands for executing browser automation tasks,
    replaying recorded sessions, and healing failed sessions.
    """
    pass


if __name__ == "__main__":
    app()
