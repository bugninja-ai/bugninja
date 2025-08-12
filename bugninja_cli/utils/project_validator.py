"""
Project validation utilities for Bugninja CLI commands.

This module provides **decorators and utilities** to ensure CLI commands
only run in properly initialized Bugninja projects with comprehensive
validation and error handling.

## Key Components

1. **require_bugninja_project** - Decorator for project validation
2. **get_project_info** - Project information retrieval
3. **display_project_info** - Rich project information display

## Usage Examples

```python
from bugninja_cli.utils.project_validator import require_bugninja_project

@require_bugninja_project
def my_command(project_root: Path):
    # Command logic here
    print(f"Running in project: {project_root}")
```
"""

import functools
from pathlib import Path
from typing import Any, Callable, Dict

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .initialization import get_project_root, validate_project_structure

console = Console()


def require_bugninja_project(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to ensure commands only run in initialized Bugninja projects.

    This decorator validates that the current directory or a parent directory
    contains a valid Bugninja project before executing the decorated function.
    It provides comprehensive error messages and automatically adds the project
    root to the function's keyword arguments.

    Args:
        func (Callable[..., Any]): Function to decorate

    Returns:
        Callable[..., Any]: Decorated function that validates project before execution

    Raises:
        click.Abort: If not in a valid Bugninja project or project structure is invalid

    Example:
        ```python
        from bugninja_cli.utils.project_validator import require_bugninja_project

        @require_bugninja_project
        def run_task(project_root: Path, task_name: str):
            print(f"Running task '{task_name}' in project: {project_root}")
            # Task execution logic here

        # Usage
        run_task(task_name="login-flow")
        # project_root is automatically added to kwargs
        ```
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Check if we're in a Bugninja project
        project_root = get_project_root()

        if project_root is None:
            console.print(
                Panel(
                    Text(
                        "❌ Not in a Bugninja project.\n\n"
                        "To initialize a new project, run:\n"
                        "  bugninja init --name <project-name>\n\n"
                        "Or navigate to an existing Bugninja project directory.",
                        style="red",
                    ),
                    title="Project Not Found",
                    border_style="red",
                )
            )
            raise click.Abort()

        # Validate project structure
        if not validate_project_structure(project_root):
            console.print(
                Panel(
                    Text(
                        f"❌ Invalid Bugninja project structure in {project_root}\n\n"
                        "The project may be corrupted or incomplete.\n"
                        "Try reinitializing with:\n"
                        "  bugninja init --name <project-name> --force",
                        style="red",
                    ),
                    title="Invalid Project Structure",
                    border_style="red",
                )
            )
            raise click.Abort()

        # Add project root to kwargs for use in the command
        kwargs["project_root"] = project_root

        return func(*args, **kwargs)

    return wrapper


def get_project_info(project_root: Path) -> Dict[str, Any]:
    """Get information about the current project.

    This function retrieves comprehensive information about a Bugninja project
    including project name, configuration settings, and directory structure.

    Args:
        project_root (Path): Root directory of the project

    Returns:
        Dict[str, Any]: Dictionary with project information including:
            - name: Project name from configuration
            - root: Project root directory path
            - config: Complete configuration dictionary

    Example:
        ```python
        from bugninja_cli.utils.project_validator import get_project_info

        project_info = get_project_info(Path("./my-project"))
        print(f"Project: {project_info['name']}")
        print(f"Location: {project_info['root']}")
        ```
    """
    try:
        from bugninja.config import TOMLConfigLoader

        loader = TOMLConfigLoader(project_root / "bugninja.toml")
        config: Dict[str, Any] = loader.load_config()

        return {
            "name": config.get("project.name", "Unknown"),
            "root": project_root,
            "config": config,
        }
    except Exception:
        return {
            "name": "Unknown",
            "root": project_root,
            "config": {},
        }


def display_project_info(project_root: Path) -> None:
    """Display information about the current project.

    This function displays comprehensive project information using Rich
    formatting, including project name, location, and directory status.

    Args:
        project_root (Path): Root directory of the project

    Example:
        ```python
        from bugninja_cli.utils.project_validator import display_project_info

        display_project_info(Path("./my-project"))
        # Displays rich formatted project information
        ```

    Notes:
        - Uses Rich console for formatted output
        - Shows directory status (exists/missing) with color coding
        - Displays project name and location
        - Provides visual feedback for project structure
    """
    project_info = get_project_info(project_root)

    info_text = Text()
    info_text.append("📁 Project: ", style="bold")
    info_text.append(f"{project_info['name']}\n", style="blue")
    info_text.append("📍 Location: ", style="bold")
    info_text.append(f"{project_root}\n", style="blue")

    # Show directory status
    directories = ["traversals", "screenshots", "tasks"]
    info_text.append("\n📂 Directories:\n", style="bold")

    for dir_name in directories:
        dir_path = project_root / dir_name
        if dir_path.exists():
            info_text.append(f"  ✅ {dir_name}/\n", style="green")
        else:
            info_text.append(f"  ❌ {dir_name}/ (missing)\n", style="red")

    console.print(Panel(info_text, title="Project Information", border_style="blue"))
