"""
Project validation utilities for Bugninja CLI commands.

This module provides decorators and utilities to ensure CLI commands
only run in properly initialized Bugninja projects.
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

    Args:
        func: Function to decorate

    Returns:
        Decorated function that validates project before execution
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

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary with project information
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

    Args:
        project_root: Root directory of the project
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
