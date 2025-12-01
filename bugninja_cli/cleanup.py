"""
Cleanup command for Bugninja CLI.

This module provides the **cleanup command** for managing retention policies
and cleaning up old testcase-related media files (videos, screenshots) and
traversal files based on configurable rules.

## Key Features

1. **Retention Policy Enforcement** - Automatically clean up old runs based on age, count, and retention rules
2. **Configurable Rules** - Age-based deletion, maximum run limits, and per-testcase retention
3. **Dry Run Mode** - Preview what would be deleted without actually deleting
4. **Comprehensive Reporting** - Detailed summary of cleanup operations

## Usage Examples

```bash
# Run cleanup with default settings (14 days, 10 max runs, keep last 2)
bugninja cleanup

# Preview what would be deleted (dry run)
bugninja cleanup --dry-run

# Custom retention settings
bugninja cleanup --max-age-days 30 --max-runs 20 --keep-last 5

# Cleanup without deleting traversal files
bugninja cleanup --no-cleanup-traversals
```
"""

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.retention_policy_manager import (
    CleanupSummary,
    RetentionPolicyConfig,
    RetentionPolicyManager,
    TaskCleanupResult,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview what would be deleted without actually deleting",
)
@require_bugninja_project
def cleanup(
    dry_run: bool,
    project_root: Path,
) -> None:
    """Clean up old testcase runs based on retention policy.

    This command enforces simplified retention policies for testcase-related media files
    (videos, screenshots) and traversal files. It applies two rules:

    1. **Always keep last N runs**: No matter how old, always keep the last N runs
       (default: 2) per testcase per run type
    2. **Age-based retention**: Keep runs younger than max_age_days (default: 14 days)

    Rules are applied separately to AI-navigated runs and replay runs.

    Configuration is loaded exclusively from `bugninja.toml` under the `[retention_policy]` section.
    Edit `bugninja.toml` to change retention policy settings.

    Args:
        dry_run (bool): Preview mode without actual deletion
        project_root (Path): Root directory of the Bugninja project

    Example:
        ```bash
        # Run cleanup with settings from bugninja.toml
        bugninja cleanup

        # Preview what would be deleted
        bugninja cleanup --dry-run
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Configuration is loaded exclusively from `bugninja.toml` `[retention_policy]` section
        - Edit `bugninja.toml` to modify retention policy settings
        - Cleanup is applied separately to AI runs and replay runs
        - The 'always keep last N runs' rule takes precedence - these runs are never deleted
        - Use --dry-run to preview changes before applying them
    """
    # Load configuration from TOML
    try:
        from bugninja.config import TOMLConfigLoader

        loader = TOMLConfigLoader(project_root / "bugninja.toml")
        toml_config = loader.load_config()
        retention_config = toml_config.get("retention_policy", {})
    except Exception as e:
        console.print(
            f"❌ Failed to load retention policy from bugninja.toml: {e}",
            style="red",
        )
        raise click.Abort()

    # Get values from TOML or use defaults
    max_age_days_value = retention_config.get("max_age_days", 14)
    keep_last_value = retention_config.get("keep_last_runs", 2)
    cleanup_traversals_value = retention_config.get("cleanup_traversals", True)

    # Validate configuration
    if max_age_days_value < 0:
        console.print("❌ max-age-days must be non-negative", style="red")
        raise click.Abort()

    if keep_last_value < 0:
        console.print("❌ keep-last-runs must be non-negative", style="red")
        raise click.Abort()

    # Create retention policy configuration
    config = RetentionPolicyConfig(
        max_age_days=max_age_days_value,
        keep_last_runs=keep_last_value,
        cleanup_traversals=cleanup_traversals_value,
    )

    # Display configuration
    if dry_run:
        console.print(
            Panel(
                Text(
                    "🔍 DRY RUN MODE\n\n"
                    "Previewing cleanup operations. No files will be deleted.",
                    style="yellow",
                ),
                title="Dry Run",
                border_style="yellow",
            )
        )

    console.print(
        Panel(
            Text(
                f"📋 Retention Policy Configuration (from bugninja.toml):\n\n"
                f"  • Max Age: {max_age_days_value} days\n"
                f"  • Keep Last Runs: {keep_last_value}\n"
                f"  • Cleanup Traversals: {config.cleanup_traversals}",
                style="cyan",
            ),
            title="Configuration",
            border_style="cyan",
        )
    )

    # Create retention policy manager
    manager = RetentionPolicyManager(project_root, config)

    # Run cleanup
    console.print("\n🧹 Starting cleanup process...\n")
    summary = manager.cleanup_all_tasks(dry_run=dry_run)

    # Display results
    _display_cleanup_summary(summary, dry_run)


def _display_cleanup_summary(summary: CleanupSummary, dry_run: bool) -> None:
    """Display cleanup summary in a formatted table.

    Args:
        summary (CleanupSummary): Summary of cleanup operation
        dry_run (bool): Whether this was a dry run
    """
    if summary.total_tasks_processed == 0:
        console.print(
            Panel(
                Text(
                    "📭 No tasks found to process.\n\n"
                    "Tasks are located in the 'tasks/' directory.",
                    style="yellow",
                ),
                title="No Tasks",
                border_style="yellow",
            )
        )
        return

    # Create summary table
    table = Table(title="🧹 Cleanup Summary", show_header=True, header_style="bold magenta")

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="bold")

    action_text = "Would delete" if dry_run else "Deleted"

    table.add_row("Tasks Processed", str(summary.total_tasks_processed))
    table.add_row("Tasks Failed", str(summary.total_tasks_failed))
    table.add_row(f"{action_text} AI Runs", str(summary.total_deleted_ai_runs))
    table.add_row(f"{action_text} Replay Runs", str(summary.total_deleted_replay_runs))
    table.add_row(f"{action_text} Videos", str(summary.total_deleted_videos))
    table.add_row(f"{action_text} Screenshots", str(summary.total_deleted_screenshots))
    table.add_row(f"{action_text} Traversals", str(summary.total_deleted_traversals))

    console.print(table)

    # Display per-task details if there were deletions
    if summary.total_deleted_ai_runs > 0 or summary.total_deleted_replay_runs > 0:
        _display_per_task_details(summary.task_results, dry_run)

    # Display errors if any
    if summary.errors:
        console.print("\n❌ Errors encountered during cleanup:", style="red")
        for error in summary.errors:
            console.print(f"  • {error}", style="red")

    # Final message
    if dry_run:
        console.print(
            "\n💡 This was a dry run. Use 'bugninja cleanup' (without --dry-run) to apply changes.",
            style="yellow",
        )
    else:
        total_deleted = (
            summary.total_deleted_ai_runs
            + summary.total_deleted_replay_runs
            + summary.total_deleted_videos
            + summary.total_deleted_screenshots
            + summary.total_deleted_traversals
        )
        if total_deleted > 0:
            console.print(
                f"\n✅ Cleanup completed successfully. {total_deleted} items deleted.",
                style="green",
            )
        else:
            console.print("\n✅ No items needed cleanup.", style="green")


def _display_per_task_details(task_results: list[TaskCleanupResult], dry_run: bool) -> None:
    """Display per-task cleanup details.

    Args:
        task_results: List of TaskCleanupResult objects
        dry_run: Whether this was a dry run
    """
    # Filter to only show tasks with deletions
    tasks_with_deletions = [
        r
        for r in task_results
        if r.deleted_ai_runs > 0
        or r.deleted_replay_runs > 0
        or r.deleted_videos > 0
        or r.deleted_screenshots > 0
        or r.deleted_traversals > 0
    ]

    if not tasks_with_deletions:
        return

    console.print("\n📊 Per-Task Details:", style="bold")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Task", style="cyan")
    table.add_column("AI Runs", justify="right", style="blue")
    table.add_column("Replay Runs", justify="right", style="green")
    table.add_column("Videos", justify="right")
    table.add_column("Screenshots", justify="right")
    table.add_column("Traversals", justify="right")

    for result in tasks_with_deletions:
        if (
            result.deleted_ai_runs > 0
            or result.deleted_replay_runs > 0
            or result.deleted_videos > 0
            or result.deleted_screenshots > 0
            or result.deleted_traversals > 0
        ):
            table.add_row(
                result.task_name,
                str(result.deleted_ai_runs),
                str(result.deleted_replay_runs),
                str(result.deleted_videos),
                str(result.deleted_screenshots),
                str(result.deleted_traversals),
            )

    console.print(table)

    # Show errors for specific tasks
    tasks_with_errors = [r for r in task_results if r.errors]
    if tasks_with_errors:
        console.print("\n⚠️  Task-specific errors:", style="yellow")
        for result in tasks_with_errors:
            console.print(f"  • {result.task_name}:", style="yellow")
            for error in result.errors:
                console.print(f"    - {error}", style="red")
