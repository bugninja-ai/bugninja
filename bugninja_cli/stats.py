from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.project_validator import (
    display_project_info,
    require_bugninja_project,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.option(
    "--list",
    "-l",
    "list_flag",
    is_flag=True,
    help="List all available runs",
)
@click.option(
    "--id",
    "run_id",
    required=False,
    type=str,
    help="Show statistics for specific run ID",
)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information",
)
@require_bugninja_project
def stats(
    list_flag: bool,
    run_id: str,
    info: bool,
    project_root: Path,
) -> None:
    """Show `statistics` about specific runs"""

    if info:
        display_project_info(project_root)

    if list_flag:
        console.print(Panel("📊 Listing all runs...", title="Stats Command", border_style="blue"))
        # TODO: Implement listing all runs
    elif run_id:
        console.print(
            Panel(
                f"📊 Showing statistics for run: {run_id}",
                title="Stats Command",
                border_style="blue",
            )
        )
        # TODO: Implement showing specific run statistics
    else:
        console.print(
            Panel(
                Text(
                    "📊 Project Statistics\n\nUse:\n  -l, --list: List all runs\n  --id <run_id>: Show specific run statistics",
                    style="cyan",
                ),
                title="Statistics",
                border_style="blue",
            )
        )
