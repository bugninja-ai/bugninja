"""
Add task command for Bugninja CLI.

This module provides the **add command** for creating new tasks in a Bugninja project.
It creates a complete task structure with description, metadata, and environment files.

## Key Features

1. **Task Creation** - Creates new tasks with unique CUID2 identifiers
2. **File Structure** - Generates complete task file structure
3. **Validation** - Ensures task name uniqueness and validity
4. **Rich Output** - Provides clear feedback and file locations

## Usage Examples

```bash
# Create a new task
bugninja add "Login Flow"

# Create another task
bugninja add "User Registration"
```
"""

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.completion import complete_task_names
from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.style import MARKDOWN_CONFIG
from bugninja_cli.utils.task_manager import TaskManager, name_to_snake_case

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.argument(
    "task_name",
    type=str,
)
@click.option(
    "--depends",
    "depends",
    multiple=True,
    shell_complete=complete_task_names,
    help="Names of testcases this task depends on (provide multiple).",
)
@require_bugninja_project
def add(task_name: str, project_root: Path, depends: tuple[str, ...]) -> None:
    """Create a new task in the current Bugninja project.

    This command creates a **complete task structure** including:
    - task directory with snake_case folder name
    - task configuration file (task_{folder_name}.toml) with embedded secrets
    - task metadata embedded in TOML configuration

    Args:
        task_name (str): Name of the task to create
        project_root (Path): Root directory of the Bugninja project
        depends (Tuple[str, ...]): Optional dependency testcase names

    Raises:
        click.Abort: If task already exists or creation fails

    Example:
        ```bash
        # Create a new task
        bugninja add "Login Flow"

        # Create another task with dependencies
        bugninja add "Checkout Flow" --depends "Login Flow" "Add To Cart"
        ```
    """
    try:
        # Initialize task manager
        task_manager = TaskManager(project_root)

        # Create the task
        deps_list = list(depends) if depends else None
        task_id = task_manager.create_task(task_name, dependencies=deps_list)
        folder_name = name_to_snake_case(task_name)

        # Build success message
        task_dir = project_root / "tasks" / folder_name
        success_text = Text()
        success_text.append("✅ ", style="green")
        success_text.append(f"Task '{task_name}' created successfully!\n\n", style="bold")

        success_text.append("📁 Task location:\n", style="bold")
        success_text.append(f"  • {task_dir}\n\n", style="blue")

        success_text.append("📄 Created files:\n", style="bold")
        success_text.append(
            f"  • {task_dir / f'task_{folder_name}.toml'} (task configuration and secrets)\n",
            style="blue",
        )

        if deps_list:
            success_text.append("\n🔗 Dependencies added:\n", style="bold")
            for d in deps_list:
                success_text.append(f"  • {d}\n", style="cyan")

        success_text.append("🚀 Next steps:\n", style="bold")
        success_text.append(
            f"  1. Edit the task configuration in task_{folder_name}.toml\n", style="cyan"
        )
        success_text.append(
            "  2. Update the start_url field with your target website URL\n", style="cyan"
        )
        success_text.append(
            "  3. Add your secrets in the [secrets] section of the TOML file\n", style="cyan"
        )
        success_text.append(
            "  4. Configure I/O schemas for data extraction if needed\n", style="cyan"
        )
        success_text.append(
            f"  5. Run 'bugninja run {folder_name}' or 'bugninja run {task_id}' to execute\n",
            style="cyan",
        )

        console.print(Panel(success_text, title="🎉 Task Created", border_style="green"))

    except ValueError as e:
        # Handle validation errors (task already exists, invalid name, etc.)
        error_text = Text()
        error_text.append("❌ ", style="red")
        error_text.append(str(e), style="red")

        if "already exists" in str(e):
            error_text.append(
                "\n\n💡 Tip: Use a different task name or check existing tasks.", style="yellow"
            )

        console.print(Panel(error_text, title="Task Creation Failed", border_style="red"))
        raise click.Abort()

    except Exception as e:
        # Handle unexpected errors
        console.print(
            Panel(
                Text(f"❌ Failed to create task: {e}", style="red"),
                title="Task Creation Failed",
                border_style="red",
            )
        )
        raise click.Abort()
