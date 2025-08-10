from pathlib import Path
from typing import List

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
    "-a",
    "--all",
    "all_flag",
    required=False,
    is_flag=True,
    help="Replay all available traversals in `traversals` folder",
)
@click.option(
    "-t",
    "--traversal",
    "traversal",
    required=False,
    type=str,
    help="Replay specific traversal with the given ID",
)
@click.option(
    "-mt",
    "--multiple",
    "multiple",
    required=False,
    type=str,
    multiple=True,
    help="Replay multiple traversals with the given IDs",
)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information before replaying",
)
@require_bugninja_project
def replay(
    all_flag: bool,
    traversal: str,
    multiple: List[str],
    info: bool,
    project_root: Path,
) -> None:
    """Run `replay` on one or multiple traversals"""

    if info:
        display_project_info(project_root)

    if all_flag:
        console.print(
            Panel("🔄 Replaying all traversals...", title="Replay Command", border_style="blue")
        )
        # TODO: Implement replaying all traversals
    elif traversal:
        console.print(
            Panel(
                f"🔄 Replaying traversal: {traversal}", title="Replay Command", border_style="blue"
            )
        )
        # TODO: Implement replaying specific traversal
    elif multiple:
        console.print(
            Panel(
                f"🔄 Replaying multiple traversals: {', '.join(multiple)}",
                title="Replay Command",
                border_style="blue",
            )
        )
        # TODO: Implement replaying multiple traversals
    else:
        console.print(
            Panel(
                Text(
                    "❌ No traversal specified.\n\nUse one of:\n  -a, --all: Replay all traversals\n  -t, --traversal <id>: Replay specific traversal\n  -mt, --multiple <id1> <id2>: Replay multiple traversals",
                    style="red",
                ),
                title="No Traversal Specified",
                border_style="red",
            )
        )
