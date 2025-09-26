"""
Statistics command for Bugninja CLI.

This module provides the **stats command** for displaying statistics and information
about automation runs with comprehensive task statistics and run history.

## Key Features

1. **Task Statistics** - Display comprehensive task run statistics
2. **Run History** - Show AI runs vs replay runs for each task
3. **Success Tracking** - Display last run status and success rates
4. **Rich Tables** - Beautiful formatted output using Rich tables

## Usage Examples

```bash
# Show task statistics
bugninja stats

# Show project information
bugninja stats --info

# Show both project info and task statistics
bugninja stats --info
```
"""

from pathlib import Path
from typing import List

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bugninja_cli.utils.project_validator import (
    display_project_info,
    require_bugninja_project,
)
from bugninja_cli.utils.stats_collector import StatsCollector, TaskStats
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information",
)
@require_bugninja_project
def stats(
    info: bool,
    project_root: Path,
) -> None:
    """Display statistics and information about automation runs.

    This command provides **comprehensive task statistics** including run counts,
    success rates, and last run status for all tasks in the project.

    Args:
        info (bool): Whether to show project information
        project_root (Path): Root directory of the Bugninja project

    Raises:
        click.Abort: If not in a valid Bugninja project

    Example:
        ```bash
        # Show task statistics
        bugninja stats

        # Show project information
        bugninja stats --info

        # Show both project info and task statistics
        bugninja stats --info
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Statistics are generated from run_history.json files in each task directory
        - Shows AI runs, replay runs, and last run status for each task
        - Handles missing or corrupted run history files gracefully
    """
    if info:
        display_project_info(project_root)

    # Collect statistics from all tasks
    stats_collector = StatsCollector(project_root)
    task_stats = stats_collector.collect_all_task_stats()

    if not task_stats:
        console.print(
            Panel(
                Text(
                    "📊 No tasks found in this project.\n\n"
                    "Create tasks with:\n"
                    '  bugninja add --name "My Task"',
                    style="yellow",
                ),
                title="No Tasks Found",
                border_style="yellow",
            )
        )
        return

    # Create and display the statistics table
    _display_task_statistics_table(task_stats)


def _display_task_statistics_table(task_stats: List[TaskStats]) -> None:
    """Display task statistics in a Rich table.

    Args:
        task_stats: List of TaskStats objects to display
    """
    # Create the table
    table = Table(title="📊 Task Statistics", show_header=True, header_style="bold magenta")

    # Add columns in the requested order
    table.add_column("Task Name", style="cyan", no_wrap=True)
    table.add_column("Last Status", justify="center", style="bold")
    table.add_column("Last Run", style="dim")
    table.add_column("Last Run Type", justify="center", style="blue")
    table.add_column("Total Runs", justify="right", style="bold")
    table.add_column("AI Runs", justify="right", style="blue")
    table.add_column("Replay Runs", justify="right", style="green")
    table.add_column("Error Type", style="red")

    # Add rows
    for stats in task_stats:
        table.add_row(
            stats.task_name,
            stats.last_status,
            stats.last_run_time,
            stats.last_run_type,
            str(stats.total_runs),
            str(stats.ai_runs),
            str(stats.replay_runs),
            stats.error_type,
        )

    # Display the table
    console.print(table)
