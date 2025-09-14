from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.project_validator import (
    display_project_info,
    require_bugninja_project,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG
from bugninja_cli.utils.task_executor import TaskExecutor
from bugninja_cli.utils.task_manager import TaskManager

if TYPE_CHECKING:
    from bugninja.schemas import TaskInfo

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
@click.option(
    "-t",
    "--task",
    "task",
    required=False,
    type=str,
    help="Runs specific task with the given ID",
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
# @click.option(
#     "--headless",
#     is_flag=True,
#     default=True,
#     help="Run browser in headless mode (default: True)",
# )
@click.option(
    "--enable-logging",
    is_flag=False,
    flag_value=True,
    default=False,
    help="Enable Bugninja logging (true/false)",
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
    # headless: bool,
    enable_logging: bool,
    info: bool,
    project_root: Path,
) -> None:
    """Execute browser automation tasks with AI-powered navigation.

    This command provides **task execution capabilities** for browser automation
    using AI-powered agents. It supports single task execution, multiple task
    execution, and bulk execution of all available tasks.

    Args:
        all_flag (bool): Whether to run all available tasks
        task (str): ID of specific task to run
        multiple (List[str]): List of task IDs to run
        info (bool): Whether to show project information before running
        project_root (Path): Root directory of the Bugninja project

    Raises:
        click.Abort: If not in a valid Bugninja project or no task specified

    Example:
        ```bash
        # Run all available tasks
        bugninja run --all

        # Run specific task
        bugninja run --task login-flow

        # Run multiple tasks
        bugninja run --multiple task1 task2 task3

        # Show project info before running
        bugninja run --task login-flow --info
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Task definitions must exist in the `tasks/` directory
        - Tasks are executed using AI-powered navigation agents
        - Each task creates a traversal that can be replayed later
    """
    if info:
        display_project_info(project_root)

    # Initialize task manager
    task_manager = TaskManager(project_root)

    async def run_tasks() -> None:

        task_info = _get_task_by_identifier(task_manager, task)

        if not task_info:
            console.print(
                Panel(
                    Text(
                        f"❌ Task '{task}' not found.\n\n"
                        "Available tasks:\n"
                        + "\n".join(
                            [
                                f"  • {task.name} ({task.folder_name})"
                                for task in task_manager.list_tasks()
                            ]
                        ),
                        style="red",
                    ),
                    title="Task Not Found",
                    border_style="red",
                )
            )
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


def _get_task_by_identifier(task_manager: TaskManager, identifier: str) -> Optional[TaskInfo]:
    """Get task by folder name or CUID.

    Args:
        task_manager (TaskManager): Task manager instance
        identifier (str): Task identifier (folder name or CUID)

    Returns:
        TaskInfo: Task information if found, None otherwise
    """
    # First try folder name lookup
    task: Optional[TaskInfo] = task_manager.get_task_by_name(identifier)
    if task:
        return task

    # Then try CUID lookup
    task = task_manager.get_task_by_cuid(identifier)
    if task:
        return task

    return None


async def _run_single_task(
    executor: TaskExecutor, task_manager: TaskManager, task_identifier: str
) -> None:
    """Run a single task.

    Args:
        executor (TaskExecutor): Task executor instance
        task_manager (TaskManager): Task manager instance
        task_identifier (str): Task identifier (folder name or CUID)
        headless (bool): Whether to run in headless mode
    """
    # Find the task
    task_info = _get_task_by_identifier(task_manager, task_identifier)

    if not task_info:
        console.print(
            Panel(
                Text(
                    f"❌ Task '{task_identifier}' not found.\n\n"
                    "Available tasks:\n"
                    + "\n".join(
                        [
                            f"  • {task.name} ({task.folder_name})"
                            for task in task_manager.list_tasks()
                        ]
                    ),
                    style="red",
                ),
                title="Task Not Found",
                border_style="red",
            )
        )
        return

    # Execute the task
    console.print(
        Panel(f"🔄 Running task: {task_info.name}", title="Run Command", border_style="blue")
    )

    # Show which config files are being used
    console.print(f"📄 Using configuration: {task_info.toml_path}")
    if task_info.env_path.exists():
        console.print(f"🔐 Using secrets: {task_info.env_path}")
    else:
        console.print(f"ℹ️  No secrets file found: {task_info.env_path}")

    try:
        result = await executor.execute_task(task_info)

        # Show summary
        if result.success:
            console.print(
                Panel(
                    Text(
                        (
                            f"✅ Task '{task_info.name}' completed successfully!\n\n"
                            f"⏱️ Execution time: {result.execution_time:.2f} seconds\n"
                            f"📁 Traversal saved: {result.traversal_path}"
                            if result.traversal_path
                            else "📁 No traversal file generated"
                        ),
                        style="green",
                    ),
                    title="Task Completed",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    Text(
                        f"❌ Task '{task_info.name}' failed!\n\n"
                        f"⏱️ Execution time: {result.execution_time:.2f} seconds\n"
                        f"🚨 Error: {result.error_message}",
                        style="red",
                    ),
                    title="Task Failed",
                    border_style="red",
                )
            )
    except Exception as e:
        console.print(
            Panel(
                Text(f"❌ Failed to execute task '{task_info.name}': {e}", style="red"),
                title="Execution Error",
                border_style="red",
            )
        )


# async def _run_multiple_tasks(
#     executor: TaskExecutor, task_manager: TaskManager, task_identifiers: List[str]
# ) -> None:
#     """Run multiple tasks in parallel.

#     Args:
#         executor (TaskExecutor): Task executor instance
#         task_manager (TaskManager): Task manager instance
#         task_identifiers (List[str]): List of task identifiers
#         headless (bool): Whether to run in headless mode
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
#         headless (bool): Whether to run in headless mode
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
