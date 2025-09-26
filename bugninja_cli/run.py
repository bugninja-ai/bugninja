"""
Run command for Bugninja CLI.

This module provides the **run command** for executing browser automation tasks
using AI-powered navigation agents. It supports single task execution with
comprehensive configuration and logging options.

## Key Features

1. **Task Execution** - Execute individual tasks with AI-powered navigation
2. **Configuration Loading** - Loads task-specific configuration from TOML files
3. **Logging Support** - Optional Bugninja logging for debugging
4. **Rich Output** - Provides detailed feedback and progress information
5. **Metadata Updates** - Updates task metadata after execution

## Usage Examples

```bash
# Run a specific task
bugninja run --task login-flow

# Run with logging enabled
bugninja run --task login-flow --enable-logging

# Show project info before running
bugninja run --task login-flow --info
```
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel

from bugninja_cli.utils.completion import complete_boolean_values, complete_task_names
from bugninja_cli.utils.project_validator import (
    display_project_info,
    require_bugninja_project,
)
from bugninja_cli.utils.result_display import (
    display_execution_error,
    display_task_failure,
    display_task_not_found,
    display_task_success,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG
from bugninja_cli.utils.task_executor import TaskExecutor
from bugninja_cli.utils.task_lookup import (
    get_available_tasks_list,
    get_task_by_identifier,
)
from bugninja_cli.utils.task_manager import TaskManager

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
# @click.option(
#     "-a",
#     "--all",
#     "all_flag",
#     required=False,
#     is_flag=True,
#     help="Run all available possible task in `tasks` folder",
# )
@click.argument(
    "task",
    type=str,
    shell_complete=complete_task_names,
)
# @click.option(
#     "-mt",
#     "--multiple",
#     "multiple",
#     required=False,
#     type=str,
#     multiple=True,
#     help="Runs multiple tasks with the given IDs",
# )
@click.option(
    "--enable-logging",
    is_flag=False,
    flag_value=True,
    default=False,
    help="Enable Bugninja logging (true/false)",
    shell_complete=complete_boolean_values,
)
@click.option(
    "--info",
    is_flag=True,
    help="Show project information before running",
)
@require_bugninja_project
def run(
    # all_flag: bool,
    task: str,
    # multiple: List[str],
    enable_logging: bool,
    info: bool,
    project_root: Path,
) -> None:
    """Execute browser automation tasks with AI-powered navigation.

    This command provides **task execution capabilities** for browser automation
    using AI-powered agents. It supports single task execution with comprehensive
    configuration and logging options.

    Args:
        task (Optional[str]): ID or name of specific task to run
        enable_logging (bool): Whether to enable Bugninja logging (default: False)
        info (bool): Whether to show project information before running
        project_root (Path): Root directory of the Bugninja project

    Raises:
        click.Abort: If not in a valid Bugninja project or no task specified

    Example:
        ```bash
        # Run specific task
        bugninja run login-flow

        # Run with logging enabled
        bugninja run login-flow --enable-logging

        # Show project info before running
        bugninja run login-flow --info
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Task definitions must exist in the `tasks/` directory
        - Tasks are executed using AI-powered navigation agents
        - Each task creates a traversal that can be replayed later
        - Task can be identified by folder name or CUID
        - Configuration is loaded from task-specific TOML files
    """
    if info:
        display_project_info(project_root)

    # Initialize task manager
    task_manager = TaskManager(project_root)

    async def run_tasks() -> None:

        task_info = get_task_by_identifier(task_manager, task)

        if not task_info:
            available_tasks = get_available_tasks_list(task_manager)
            display_task_not_found(task, available_tasks)
            return

        # Load task run configuration from TOML
        task_run_config = TaskExecutor._load_task_run_config(task_info.toml_path)

        """Async function to run tasks."""
        async with TaskExecutor(
            task_run_config=task_run_config,
            project_root=project_root,
            enable_logging=enable_logging,
        ) as executor:
            # if all_flag:
            #     await _run_all_tasks(executor, task_manager)
            # elif task:
            await _run_single_task(executor, task_manager, task)
            # elif multiple:
            #     await _run_multiple_tasks(executor, task_manager, multiple)
            # else:
            #     _show_no_task_error()

    # Run the async function
    asyncio.run(run_tasks())


async def _run_single_task(
    executor: TaskExecutor, task_manager: TaskManager, task_identifier: str
) -> None:
    """Run a single task.

    Args:
        executor (TaskExecutor): Task executor instance
        task_manager (TaskManager): Task manager instance
        task_identifier (str): Task identifier (folder name or CUID)
    """
    # Find the task
    task_info = get_task_by_identifier(task_manager, task_identifier)

    if not task_info:
        available_tasks = get_available_tasks_list(task_manager)
        display_task_not_found(task_identifier, available_tasks)
        return

    # Execute the task
    console.print(
        Panel(f"🔄 Running task: {task_info.name}", title="Run Command", border_style="blue")
    )

    # Show which config files are being used
    console.print(f"📄 Using configuration: {task_info.toml_path}")

    try:
        result = await executor.execute_task(task_info)

        # Show summary
        if result.success:
            display_task_success(task_info, result)
        else:
            display_task_failure(task_info, result)
    except Exception as e:
        display_execution_error(task_info, e)


# async def _run_multiple_tasks(
#     executor: TaskExecutor, task_manager: TaskManager, task_identifiers: List[str]
# ) -> None:
#     """Run multiple tasks in parallel.

#     Args:
#         executor (TaskExecutor): Task executor instance
#         task_manager (TaskManager): Task manager instance
#         task_identifiers (List[str]): List of task identifiers
#     """
#     # Find all tasks
#     task_infos = []
#     not_found = []

#     for identifier in task_identifiers:
#         task_info = _get_task_by_identifier(task_manager, identifier)
#         if task_info:
#             task_infos.append(task_info)
#         else:
#             not_found.append(identifier)

#     # Show not found tasks
#     if not_found:
#         console.print(
#             Panel(
#                 Text(
#                     f"❌ Tasks not found: {', '.join(not_found)}\n\n"
#                     "Available tasks:\n"
#                     + "\n".join(
#                         [
#                             f"  • {task.name} ({task.folder_name})"
#                             for task in task_manager.list_tasks()
#                         ]
#                     ),
#                     style="red",
#                 ),
#                 title="Tasks Not Found",
#                 border_style="red",
#             )
#         )

#     if not task_infos:
#         console.print(
#             Panel(
#                 Text("❌ No valid tasks to execute", style="red"),
#                 title="No Tasks",
#                 border_style="red",
#             )
#         )
#         return

#     # Execute tasks
#     console.print(
#         Panel(
#             f"🔄 Running {len(task_infos)} tasks in parallel: {', '.join([task.name for task in task_infos])}",
#             title="Run Command",
#             border_style="blue",
#         )
#     )

#     try:
#         results = await executor.execute_multiple_tasks(task_infos)

#         # Show summary
#         successful = [r for r in results if r.success]
#         failed = [r for r in results if not r.success]

#         summary_text = Text()
#         summary_text.append("📊 Execution Summary:\n\n", style="bold")
#         summary_text.append(f"✅ Successful: {len(successful)}/{len(results)}\n", style="green")
#         summary_text.append(f"❌ Failed: {len(failed)}/{len(results)}\n\n", style="red")

#         if successful:
#             summary_text.append("✅ Successful tasks:\n", style="green")
#             for result in successful:
#                 summary_text.append(
#                     f"  • {result.task_info.name} ({result.execution_time:.2f}s)\n", style="green"
#                 )

#         if failed:
#             summary_text.append("\n❌ Failed tasks:\n", style="red")
#             for result in failed:
#                 summary_text.append(
#                     f"  • {result.task_info.name}: {result.error_message}\n", style="red"
#                 )

#         console.print(Panel(summary_text, title="Execution Summary", border_style="blue"))

#     except Exception as e:
#         console.print(
#             Panel(
#                 Text(f"❌ Failed to execute multiple tasks: {e}", style="red"),
#                 title="Execution Error",
#                 border_style="red",
#             )
#         )


# async def _run_all_tasks(executor: TaskExecutor, task_manager: TaskManager) -> None:
#     """Run all available tasks.

#     Args:
#         executor (TaskExecutor): Task executor instance
#         task_manager (TaskManager): Task manager instance
#     """
#     # Get all tasks
#     task_infos = task_manager.list_tasks()

#     if not task_infos:
#         console.print(
#             Panel(
#                 Text("❌ No tasks found in the project", style="red"),
#                 title="No Tasks",
#                 border_style="red",
#             )
#         )
#         return

#     # Execute all tasks
#     console.print(
#         Panel(
#             f"🔄 Running all {len(task_infos)} tasks in parallel: {', '.join([task.name for task in task_infos])}",
#             title="Run Command",
#             border_style="blue",
#         )
#     )

#     try:
#         results = await executor.execute_multiple_tasks(task_infos)

#         # Show summary
#         successful = [r for r in results if r.success]
#         failed = [r for r in results if not r.success]

#         summary_text = Text()
#         summary_text.append("📊 Execution Summary:\n\n", style="bold")
#         summary_text.append(f"✅ Successful: {len(successful)}/{len(results)}\n", style="green")
#         summary_text.append(f"❌ Failed: {len(failed)}/{len(results)}\n\n", style="red")

#         if successful:
#             summary_text.append("✅ Successful tasks:\n", style="green")
#             for result in successful:
#                 summary_text.append(
#                     f"  • {result.task_info.name} ({result.execution_time:.2f}s)\n", style="green"
#                 )

#         if failed:
#             summary_text.append("\n❌ Failed tasks:\n", style="red")
#             for result in failed:
#                 summary_text.append(
#                     f"  • {result.task_info.name}: {result.error_message}\n", style="red"
#                 )

#         console.print(Panel(summary_text, title="Execution Summary", border_style="blue"))

#     except Exception as e:
#         console.print(
#             Panel(
#                 Text(f"❌ Failed to execute all tasks: {e}", style="red"),
#                 title="Execution Error",
#                 border_style="red",
#             )
#         )


# def _show_no_task_error() -> None:
#     """Show error when no task is specified."""
#     console.print(
#         Panel(
#             Text(
#                 "❌ No task specified.\n\nUse one of:\n  -a, --all: Run all tasks\n  -t, --task <id>: Run specific task\n  -mt, --multiple <id1> <id2>: Run multiple tasks",
#                 style="red",
#             ),
#             title="No BugninjaTask Specified",
#             border_style="red",
#         )
#     )
