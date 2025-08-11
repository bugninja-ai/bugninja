"""
Bugninja project initialization utilities.

This module provides utilities for:
- Project detection and validation
- Directory management and creation
- Configuration file generation and validation
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import tomli
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def is_bugninja_project(directory: Optional[Path] = None) -> bool:
    """Check if the given directory is a Bugninja project.

    Args:
        directory: Directory to check. Defaults to current directory.

    Returns:
        True if directory contains a valid bugninja.toml file
    """
    if directory is None:
        directory = Path.cwd()

    config_file = directory / "bugninja.toml"
    return config_file.exists() and config_file.is_file()


def get_project_root() -> Optional[Path]:
    """Find the root directory of the current Bugninja project.

    Searches upward from current directory to find bugninja.toml.

    Returns:
        Path to project root if found, None otherwise
    """
    current = Path.cwd()

    # Search upward through parent directories
    while current != current.parent:
        if is_bugninja_project(current):
            return current
        current = current.parent

    return None


def validate_project_structure(project_root: Path) -> bool:
    """Validate that a Bugninja project has the required structure.

    Args:
        project_root: Root directory of the project

    Returns:
        True if project structure is valid
    """
    if not is_bugninja_project(project_root):
        return False

    # Check if config file is valid TOML
    try:
        config_file = project_root / "bugninja.toml"
        with open(config_file, "rb") as f:
            tomli.load(f)
    except Exception:
        return False

    return True


def create_project_directories(project_config: Dict[str, Any]) -> None:
    """Create all required project directories.

    Args:
        project_config: Configuration dictionary with path information
    """
    directories = []

    # Extract directory paths from config
    paths = project_config.get("paths", {})
    directories.extend(
        [
            Path(paths.get("traversals_dir", "./traversals")),
            Path(paths.get("screenshots_dir", "./screenshots")),
            Path(paths.get("tasks_dir", "./tasks")),
        ]
    )

    # Create directories
    ensure_directories_exist(directories)


def ensure_directories_exist(directories: List[Path]) -> None:
    """Ensure all specified directories exist, creating them if necessary.

    Args:
        directories: List of directory paths to create
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for directory in directories:
            task = progress.add_task(f"Creating {directory}...", total=None)

            try:
                directory.mkdir(parents=True, exist_ok=True)
                progress.update(task, description=f"✅ Created {directory}")
            except Exception as e:
                progress.update(task, description=f"❌ Failed to create {directory}: {e}")
                raise


def validate_directory_permissions(directory: Path) -> bool:
    """Validate that we have write permissions for a directory.

    Args:
        directory: Directory to check

    Returns:
        True if we have write permissions
    """
    try:
        # Try to create a temporary file to test write permissions
        test_file = directory / ".test_write_permission"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception as e:
        console.print(f"❌ Failed to validate directory permissions for {directory}: {e}")
        return False


def get_default_config_template(project_name: str, **overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Generate default configuration template.

    Args:
        project_name: Name of the project
        **overrides: Configuration overrides

    Returns:
        Configuration dictionary
    """
    config = {
        "project": {"name": project_name},
        "llm": {"model": "gpt-4.1", "temperature": 0.001, "api_version": "2024-02-15-preview"},
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "enable_rich_logging": True,
        },
        "development": {"debug_mode": False, "enable_verbose_logging": False},
        "paths": {
            "traversals_dir": "./traversals",
            "screenshots_dir": "./screenshots",
            "tasks_dir": "./tasks",
        },
        "browser": {
            "viewport_width": 1280,
            "viewport_height": 960,
            "user_agent": "",
            "device_scale_factor": 0.0,
            "timeout": 30000,
        },
        "agent": {
            "max_steps": 100,
            "planner_interval": 5,
            "enable_vision": True,
            "enable_memory": False,
            "wait_between_actions": 0.1,
        },
        "replicator": {
            "sleep_after_actions": 1.0,
            "pause_after_each_step": True,
            "fail_on_unimplemented_action": False,
            "max_retries": 2,
            "retry_delay": 0.5,
        },
        "screenshot": {"format": "png"},
        "events": {"publishers": ["null"]},
    }

    # Apply overrides
    for key, value in overrides.items():
        if key in config:
            if isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value

    return config


def write_config_file(config: Dict[str, Any], path: Path) -> None:
    """Write configuration to TOML file.

    Args:
        config: Configuration dictionary
        path: Path to write the configuration file
    """
    # Add header comment
    header = """# Bugninja Configuration
# This file contains all non-sensitive project configuration
# Sensitive data (API keys, passwords) should be stored in .env file

"""

    # Convert config to TOML format with proper formatting
    toml_content = _dict_to_toml(config)

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + toml_content)


def _dict_to_toml(data: Dict[str, Any]) -> str:
    """Convert dictionary to TOML format with proper formatting.

    Args:
        data: Dictionary to convert

    Returns:
        TOML formatted string
    """
    lines: List[str] = []

    for section_name, section_data in data.items():
        # Add blank line before sections (except the first one)
        if lines:
            lines.append("")

        # Add section header
        lines.append(f"[{section_name}]")

        # Add section content
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                if isinstance(value, list):
                    # Handle lists properly
                    if all(isinstance(item, str) for item in value):
                        # String list - use double quotes for consistency
                        formatted_list = '["' + '", "'.join(value) + '"]'
                    else:
                        # Other types
                        formatted_list = str(value)
                    lines.append(f"{key} = {formatted_list}")
                elif isinstance(value, bool):
                    lines.append(f"{key} = {str(value).lower()}")
                elif isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                else:
                    lines.append(f"{key} = {value}")

    return "\n".join(lines)


def validate_config_file(path: Path) -> bool:
    """Validate that a configuration file is valid TOML.

    Args:
        path: Path to configuration file

    Returns:
        True if file is valid TOML
    """
    try:
        with open(path, "rb") as f:
            tomli.load(f)
        return True
    except Exception:
        return False


def create_env_template(path: Path) -> None:
    """Create a template .env file.

    Args:
        path: Path to create the .env file
    """
    env_content = """# Bugninja Sensitive Configuration
# Copy this file to .env and fill in your secret values
# 
# IMPORTANT: This file contains ONLY sensitive data (API keys, passwords, tokens)
# All other configuration is now stored in bugninja.toml

# =============================================================================
# LLM Configuration (Sensitive Data Only)
# =============================================================================

# Azure OpenAI endpoint URL (required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Azure OpenAI API key (required)
AZURE_OPENAI_KEY=your-api-key-here

# =============================================================================
# Note: All other configuration (logging, paths, browser settings, etc.)
# is now managed in bugninja.toml file for better organization and version control.
# =============================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(env_content)


def create_readme_template(path: Path, project_name: str) -> None:
    """Create a README template for the project.

    Args:
        path: Path to create the README file
        project_name: Name of the project
    """
    readme_content = f"""# {project_name}

This is a Bugninja browser automation project.

## Project Structure

- `bugninja.toml` - Project configuration
- `.env` - Sensitive configuration (API keys, etc.)
- `traversals/` - Recorded browser sessions
- `screenshots/` - Screenshots from automation runs
- `tasks/` - Task definitions and descriptions

## Getting Started

1. Copy `.env.example` to `.env` and fill in your API keys
2. Define your tasks in the `tasks/` directory
3. Run automation with `bugninja run`
4. Replay sessions with `bugninja replay`

## Configuration

Edit `bugninja.toml` to customize:
- LLM settings
- Browser configuration
- Logging options
- Directory paths

For more information, see the [Bugninja documentation](https://github.com/bugninja/bugninja).
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(readme_content)
