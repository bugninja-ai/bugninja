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
    help="Run all available possible task in `tasks` folder",
)
@click.option(
    "-t",
    "--task",
    "task",
    required=False,
    type=str,
    help="Runs specific task with the given ID",
)
@click.option(
    "-mt",
    "--multiple",
    "multiple",
    required=False,
    type=str,
    multiple=True,
    help="Runs multiple tasks with the given IDs",
)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information before running",
)
@require_bugninja_project
def run(
    all_flag: bool,
    task: str,
    multiple: List[str],
    info: bool,
    project_root: Path,
) -> None:
    """Run one or multiple `traversals`"""

    if info:
        display_project_info(project_root)

    if all_flag:
        console.print(Panel("🔄 Running all tasks...", title="Run Command", border_style="blue"))
        # TODO: Implement running all tasks
    elif task:
        console.print(Panel(f"🔄 Running task: {task}", title="Run Command", border_style="blue"))
        # TODO: Implement running specific task
    elif multiple:
        console.print(
            Panel(
                f"🔄 Running multiple tasks: {', '.join(multiple)}",
                title="Run Command",
                border_style="blue",
            )
        )
        # TODO: Implement running multiple tasks
    else:
        console.print(
            Panel(
                Text(
                    "❌ No task specified.\n\nUse one of:\n  -a, --all: Run all tasks\n  -t, --task <id>: Run specific task\n  -mt, --multiple <id1> <id2>: Run multiple tasks",
                    style="red",
                ),
                title="No BugninjaTask Specified",
                border_style="red",
            )
        )
