"""
Replay command for Bugninja CLI.

This module provides the **replay command** for replaying recorded browser automation
sessions. It supports replaying by traversal ID or task name with optional healing
capabilities.

## Key Features

1. **Traversal Replay** - Replay specific traversals by run ID
2. **Task Replay** - Replay latest traversal for a task
3. **Healing Support** - Optional self-healing during replay
4. **Metadata Updates** - Updates task metadata after successful replay
5. **Rich Output** - Provides detailed feedback and progress information

## Usage Examples

```bash
# Replay by traversal ID
bugninja replay --traversal kfdvnie47ic2b87l00v7iut5

# Replay latest traversal for task
bugninja replay --task 5_secrets

# Replay with healing enabled
bugninja replay --task 5_secrets --healing

# Show project info before replaying
bugninja replay --task 5_secrets --info
```
"""

from datetime import UTC, datetime
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.completion import (
    complete_executed_tasks,
    complete_traversal_ids,
)
from bugninja_cli.utils.project_validator import (
    display_project_info,
    require_bugninja_project,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
# @click.option(
#     "-a",
#     "--all",
#     "all_flag",
#     required=False,
#     is_flag=True,
#     help="Replay all available traversals in `traversals` folder",
# )
@click.option(
    "-t",
    "--task",
    "task_name",
    required=False,
    type=str,
    help="Replay latest traversal for the specified task name",
    shell_complete=complete_executed_tasks,
)
@click.option(
    "-tr",
    "--traversal",
    "traversal_id",
    required=False,
    type=str,
    help="Replay specific traversal by its run_id",
    shell_complete=complete_traversal_ids,
)
# @click.option(
#     "-mt",
#     "--multiple",
#     "multiple",
#     required=False,
#     type=str,
#     multiple=True,
#     help="Replay multiple traversals with the given IDs",
# )
# @click.option(
#     "--enable-logging",
#     is_flag=False,
#     flag_value=True,
#     default=False,
#     help="Enable Bugninja logging (true/false)",
# )
@click.option(
    "--healing",
    is_flag=True,
    default=False,
    help="Enable healing during replay (default: False)",
)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information before replaying",
)
@require_bugninja_project
def replay(
    # all_flag: bool,
    task_name: str,
    traversal_id: str,
    # multiple: List[str],
    # enable_logging: bool,
    healing: bool,
    info: bool,
    project_root: Path,
) -> None:
    """Replay recorded browser sessions with optional healing.

    This command provides **session replay capabilities** for previously recorded
    browser automation sessions. You can replay by traversal ID or task name.

    Args:
        task_name (Optional[str]): Name of the task to replay latest traversal for
        traversal_id (Optional[str]): Run ID of specific traversal to replay
        healing (bool): Whether to enable healing during replay (default: False)
        info (bool): Whether to show project information before replaying
        project_root (Path): Root directory of the Bugninja project

    Raises:
        click.Abort: If not in a valid Bugninja project or traversal not found

    Example:
        ```bash
        # Replay by traversal ID
        bugninja replay --traversal kfdvnie47ic2b87l00v7iut5

        # Replay latest traversal for task
        bugninja replay --task 5_secrets

        # Replay with healing enabled
        bugninja replay --task 5_secrets --healing

        # Show project info before replaying
        bugninja replay --task 5_secrets --info
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Traversal files must exist in the `traversals/` directory
        - Uses original browser configuration from the traversal file
        - Healing is disabled by default for faster replay
        - Cannot specify both --task and --traversal options
        - Updates task metadata after successful replay
    """
    if info:
        display_project_info(project_root)

    # Determine what type of replay to perform
    if task_name and traversal_id:
        console.print(
            Panel(
                "❌ Cannot specify both --task and --traversal options. Choose one.",
                title="Invalid Options",
                border_style="red",
            )
        )
        return

    if task_name:
        try:
            # Import here to avoid circular imports
            from bugninja.schemas import TaskRunConfig
            from bugninja_cli.utils.task_executor import TaskExecutor

            # Replay latest traversal for task
            traversal_path = TaskExecutor.find_traversal_by_task_name(task_name, project_root)
            is_task_name = True
            console.print(
                Panel(
                    f"🔄 Replaying latest traversal for task: {task_name}",
                    title="Replay Command",
                    border_style="blue",
                )
            )

        except FileNotFoundError as e:
            console.print(
                Panel(
                    f"❌ Task not found: {str(e)}",
                    title="Task Not Found",
                    border_style="red",
                )
            )
            return
        except ValueError as e:
            console.print(
                Panel(
                    f"❌ Invalid task: {str(e)}",
                    title="Invalid Task",
                    border_style="red",
                )
            )
            return

    elif traversal_id:
        try:
            # Import here to avoid circular imports
            from bugninja.schemas import TaskRunConfig
            from bugninja_cli.utils.task_executor import TaskExecutor

            # Replay specific traversal by ID
            traversal_path = TaskExecutor.find_traversal_by_id(traversal_id, project_root)
            is_task_name = False
            console.print(
                Panel(
                    f"🔄 Replaying traversal: {traversal_id}",
                    title="Replay Command",
                    border_style="blue",
                )
            )

        except FileNotFoundError as e:
            console.print(
                Panel(
                    f"❌ Traversal not found: {str(e)}",
                    title="Traversal Not Found",
                    border_style="red",
                )
            )
            return
        except ValueError as e:
            console.print(
                Panel(
                    f"❌ Invalid traversal: {str(e)}",
                    title="Invalid Traversal",
                    border_style="red",
                )
            )
            return

    else:
        console.print(
            Panel(
                Text(
                    "❌ No replay target specified.\n\nUsage:\n"
                    "  --traversal <id>: Replay specific traversal by run_id\n"
                    "  --task <name>: Replay latest traversal for task\n"
                    "  --healing: Enable healing during replay",
                    style="red",
                ),
                title="No Replay Target Specified",
                border_style="red",
            )
        )
        return

    if task_name or traversal_id:
        try:
            # Import here to avoid circular imports
            from bugninja.schemas import TaskExecutionResult, TaskRunConfig
            from bugninja_cli.utils.task_executor import TaskExecutor

            # Create TaskExecutor with default config (will be overridden by traversal config)
            default_config = TaskRunConfig()

            # Execute replay
            async def run_replay() -> TaskExecutionResult:
                async with TaskExecutor(default_config, project_root) as executor:
                    result = await executor.replay_traversal(traversal_path, enable_healing=healing)

                    # Update task metadata if this was a task-based replay
                    if is_task_name and result.success:
                        from bugninja_cli.utils.task_manager import TaskManager

                        task_manager = TaskManager(project_root)
                        try:
                            task_info = task_manager.get_task_by_name(task_name)
                            if task_info:
                                # Update metadata with replay results
                                import tomli
                                import tomli_w

                                with open(task_info.toml_path, "rb") as f:
                                    config = tomli.load(f)

                                if "metadata" not in config:
                                    config["metadata"] = {}

                                config["metadata"]["latest_run_path"] = (
                                    str(result.traversal_path) if result.traversal_path else ""
                                )
                                config["metadata"]["latest_run_status"] = (
                                    "success" if result.success else "failed"
                                )
                                config["metadata"]["latest_run_timestamp"] = datetime.now(
                                    UTC
                                ).isoformat()

                                with open(task_info.toml_path, "wb") as f:
                                    tomli_w.dump(config, f)

                                console.print(f"📝 Updated task metadata for '{task_name}'")
                        except Exception as e:
                            console.print(f"⚠️  Warning: Failed to update task metadata: {e}")

                    return result

            # Run the async replay
            import asyncio

            result = asyncio.run(run_replay())

            # Display final result
            if result.success:
                steps_info = ""
                if (
                    result.result
                    and hasattr(result.result, "steps_completed")
                    and hasattr(result.result, "total_steps")
                ):
                    steps_info = f"\n📊 Steps completed: {result.result.steps_completed+1}/{result.result.total_steps}"

                console.print(
                    Panel(
                        f"✅ Replay completed successfully!\n"
                        f"⏱️  Execution time: {result.execution_time:.2f}s{steps_info}",
                        title="Replay Success",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"❌ Replay failed!\n"
                        f"⏱️  Execution time: {result.execution_time:.2f}s\n"
                        f"🚨 Error: {result.error_message}",
                        title="Replay Failed",
                        border_style="red",
                    )
                )

        except Exception as e:
            console.print(
                Panel(f"❌ Replay failed: {str(e)}", title="Replay Error", border_style="red")
            )
