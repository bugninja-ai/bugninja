"""
Initialize project command for Bugninja CLI.

This module provides the **init command** for creating new Bugninja projects.
It sets up the complete project structure with configuration files, directories,
and templates for immediate use.

## Key Features

1. **Project Structure** - Creates complete directory structure
2. **Configuration** - Generates bugninja.toml with default settings
3. **Templates** - Creates .env.example and README templates
4. **Validation** - Prevents overwriting existing projects
5. **Rich Output** - Provides clear feedback and next steps

## Usage Examples

```bash
# Basic initialization
bugninja init my-automation-project

# Custom directory paths
bugninja init my-project \
    --screenshots-dir ./custom-screenshots \
    --tasks-dir ./custom-tasks \
    --traversals-dir ./custom-traversals
```
"""

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.completion import (
    complete_directory_paths,
    complete_project_names,
)
from bugninja_cli.utils.initialization import (
    create_env_template,
    create_gitignore_template,
    create_project_directories,
    create_readme_template,
    get_default_config_template,
    is_bugninja_project,
    write_config_file,
)
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.argument(
    "project_name",
    type=str,
    shell_complete=complete_project_names,
)
@click.option(
    "--screenshots-dir",
    "-s",
    "screenshots_dir",
    required=False,
    type=str,
    help="Path to the screenshots directory",
    default="./screenshots",
    shell_complete=complete_directory_paths,
)
@click.option(
    "--tasks-dir",
    "-t",
    "tasks_dir",
    required=False,
    type=str,
    help="Path to the tasks directory",
    default="./tasks",
    shell_complete=complete_directory_paths,
)
@click.option(
    "--traversals-dir",
    "-tr",
    "traversals_dir",
    required=False,
    type=str,
    help="Path to the traversals directory",
    default="./traversals",
    shell_complete=complete_directory_paths,
)
def init(
    project_name: str,
    screenshots_dir: str,
    tasks_dir: str,
    traversals_dir: str,
) -> None:
    """Initialize a new Bugninja project in the current directory.

    This command creates a **complete Bugninja project structure** including:
    - project configuration file (bugninja.toml)
    - environment template (.env.example)
    - tasks directory for task definitions
    - README documentation

    Args:
        project_name (str): Name of the project to initialize
        screenshots_dir (str): Path to the screenshots directory (default: "./screenshots")
        tasks_dir (str): Path to the tasks directory (default: "./tasks")
        traversals_dir (str): Path to the traversals directory (default: "./traversals")

    Raises:
        click.Abort: If project already exists or initialization fails

    Example:
        ```bash
        # Basic initialization
        bugninja init my-automation-project

        # Custom directory paths
        bugninja init my-project \
            --screenshots-dir ./custom-screenshots \
            --tasks-dir ./custom-tasks \
            --traversals-dir ./custom-traversals
        ```
    """
    current_dir = Path.cwd()

    # Check if project already exists
    if is_bugninja_project(current_dir):
        console.print(
            Panel(
                Text(
                    "❌ A Bugninja project already exists in this directory.\n"
                    "Please delete the existing project toml first or choose a different directory.\n"
                    "- bugninja.toml",
                    style="red",
                ),
                title="Project Already Exists",
                border_style="red",
            )
        )
        return

    try:
        # Generate configuration
        config = get_default_config_template(
            project_name,
            paths={
                "traversals_dir": traversals_dir,
                "screenshots_dir": screenshots_dir,
                "tasks_dir": tasks_dir,
            },
        )

        # Create configuration file
        config_file = current_dir / "bugninja.toml"
        write_config_file(config, config_file)

        # Create project directories
        create_project_directories(config)

        # Create .env template
        env_file = current_dir / ".env.example"
        create_env_template(env_file)

        # Create .gitignore
        gitignore_file = current_dir / ".gitignore"
        create_gitignore_template(gitignore_file)

        # Create README
        readme_file = current_dir / "BUGNINJA_README.md"
        create_readme_template(readme_file, project_name)

        # Success message
        success_text = Text()
        success_text.append("✅ ", style="green")
        success_text.append(f"Project '{project_name}' initialized successfully!\n\n", style="bold")

        success_text.append("📁 Created directories:\n", style="bold")
        success_text.append(f"  • {tasks_dir}\n\n", style="blue")

        success_text.append("📄 Created files:\n", style="bold")
        success_text.append("  • bugninja.toml (project configuration)\n", style="blue")
        success_text.append("  • .env.example (environment template)\n", style="blue")
        success_text.append("  • .gitignore (git exclusions)\n", style="blue")
        success_text.append("  • BUGNINJA_README.md (project documentation)\n\n", style="blue")

        success_text.append("🚀 Next steps:\n", style="bold")
        success_text.append("  1. Copy .env.example to .env and add your API keys\n", style="cyan")
        success_text.append("  2. Define your tasks in the tasks/ directory\n", style="cyan")
        success_text.append("  3. Run 'bugninja run' to start automation\n", style="cyan")

        console.print(Panel(success_text, title="🎉 Project Initialized", border_style="green"))

    except Exception as e:
        console.print(
            Panel(
                Text(f"❌ Failed to initialize project: {e}", style="red"),
                title="Initialization Failed",
                border_style="red",
            )
        )
        raise
