"""
Bugninja project initialization utilities.

This module provides **comprehensive utilities** for:
- project detection and validation
- directory management and creation
- configuration file generation and validation
- environment template creation
- project structure setup

## Key Functions

1. **is_bugninja_project()** - Check if directory is a valid Bugninja project
2. **get_project_root()** - Find the root directory of current project
3. **create_project_directories()** - Create all required project directories
4. **get_default_config_template()** - Generate default configuration
5. **write_config_file()** - Write configuration to TOML file
6. **create_env_template()** - Create environment template file
7. **create_readme_template()** - Create README documentation

## Usage Examples

```python
from bugninja_cli.utils.initialization import (
    is_bugninja_project,
    get_project_root,
    create_project_directories
)

# Check if current directory is a Bugninja project
if is_bugninja_project():
    print("Valid project found")

# Get project root
project_root = get_project_root()

# Create project directories
config = {"paths": {"traversals_dir": "./traversals"}}
create_project_directories(config)
```
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import tomli
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def is_bugninja_project(directory: Optional[Path] = None) -> bool:
    """Check if the given directory is a Bugninja project.

    This function validates that a directory contains a valid `bugninja.toml`
    configuration file, which is the primary indicator of a Bugninja project.

    Args:
        directory (Optional[Path]): Directory to check. Defaults to current directory

    Returns:
        bool: True if directory contains a valid bugninja.toml file

    Example:
        ```python
        from bugninja_cli.utils.initialization import is_bugninja_project

        # Check current directory
        if is_bugninja_project():
            print("Current directory is a Bugninja project")

        # Check specific directory
        if is_bugninja_project(Path("./my-project")):
            print("my-project is a Bugninja project")
        ```
    """
    if directory is None:
        directory = Path.cwd()

    config_file = directory / "bugninja.toml"
    return config_file.exists() and config_file.is_file()


def get_project_root() -> Optional[Path]:
    """Find the root directory of the current Bugninja project.

    This function searches upward from the current directory through parent
    directories to find a valid Bugninja project (containing `bugninja.toml`).

    Returns:
        Optional[Path]: Path to project root if found, None otherwise

    Example:
        ```python
        from bugninja_cli.utils.initialization import get_project_root

        project_root = get_project_root()
        if project_root:
            print(f"Found project at: {project_root}")
        else:
            print("No Bugninja project found in current directory tree")
        ```
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

    This function checks that the project root contains a valid `bugninja.toml`
    configuration file that can be parsed as valid TOML.

    Args:
        project_root (Path): Root directory of the project

    Returns:
        bool: True if project structure is valid

    Raises:
        Exception: If TOML parsing fails

    Example:
        ```python
        from bugninja_cli.utils.initialization import validate_project_structure

        project_root = Path("./my-project")
        if validate_project_structure(project_root):
            print("Project structure is valid")
        else:
            print("Project structure is invalid or corrupted")
        ```
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

    This function creates the necessary directory structure for a Bugninja project
    based on the configuration settings. It creates directories for traversals,
    screenshots, and tasks.

    Args:
        project_config (Dict[str, Any]): Configuration dictionary with path information

    Raises:
        Exception: If directory creation fails

    Example:
        ```python
        from bugninja_cli.utils.initialization import create_project_directories

        config = {
            "paths": {
                "traversals_dir": "./traversals",
                "screenshots_dir": "./screenshots",
                "tasks_dir": "./tasks"
            }
        }
        create_project_directories(config)
        ```
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

    This function creates directories with progress indication and error handling.
    It uses Rich progress bars to show the creation process.

    Args:
        directories (List[Path]): List of directory paths to create

    Raises:
        Exception: If any directory creation fails

    Example:
        ```python
        from bugninja_cli.utils.initialization import ensure_directories_exist

        directories = [
            Path("./traversals"),
            Path("./screenshots"),
            Path("./tasks")
        ]
        ensure_directories_exist(directories)
        ```
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

    This function tests write permissions by attempting to create and delete
    a temporary file in the specified directory.

    Args:
        directory (Path): Directory to check

    Returns:
        bool: True if we have write permissions

    Example:
        ```python
        from bugninja_cli.utils.initialization import validate_directory_permissions

        if validate_directory_permissions(Path("./my-dir")):
            print("Directory is writable")
        else:
            print("Directory is not writable")
        ```
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

    This function creates a comprehensive default configuration for a new
    Bugninja project, including all necessary settings for LLM, browser,
    logging, and project paths.

    Args:
        project_name (str): Name of the project
        **overrides (Dict[str, Any]): Configuration overrides to apply

    Returns:
        Dict[str, Any]: Complete configuration dictionary

    Example:
        ```python
        from bugninja_cli.utils.initialization import get_default_config_template

        # Basic configuration
        config = get_default_config_template("my-project")

        # Configuration with overrides
        config = get_default_config_template(
            "my-project",
            paths={"traversals_dir": "./custom-traversals"}
        )
        ```
    """
    config = {
        "project": {"name": project_name},
        "llm": {
            "provider": "azure_openai",
            "model": "gpt-4.1",
            "temperature": 0.0,
        },
        "llm_azure_openai": {
            "api_version": "2024-02-15-preview",
        },
        "llm_openai": {
            "base_url": "https://api.openai.com/v1",
        },
        "llm_anthropic": {
            "base_url": "https://api.anthropic.com",
        },
        "llm_google_gemini": {
            "base_url": "https://generativelanguage.googleapis.com",
        },
        "llm_deepseek": {
            "base_url": "https://api.deepseek.com",
        },
        "llm_ollama": {
            "base_url": "http://localhost:11434",
        },
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

    This function writes a configuration dictionary to a TOML file with
    proper formatting and a header comment explaining the file's purpose.

    Args:
        config (Dict[str, Any]): Configuration dictionary to write
        path (Path): Path to write the configuration file

    Example:
        ```python
        from bugninja_cli.utils.initialization import write_config_file

        config = {"project": {"name": "my-project"}}
        write_config_file(config, Path("./bugninja.toml"))
        ```
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

    This function converts a Python dictionary to TOML format with proper
    section headers, value formatting, and list handling. It also handles
    nested LLM provider sections specially.

    Args:
        data (Dict[str, Any]): Dictionary to convert

    Returns:
        str: TOML formatted string

    Example:
        ```python
        from bugninja_cli.utils.initialization import _dict_to_toml

        data = {"project": {"name": "test"}, "llm": {"model": "gpt-4"}}
        toml_str = _dict_to_toml(data)
        print(toml_str)
        ```
    """
    lines: List[str] = []

    # Handle LLM sections specially
    llm_sections = []
    other_sections = {}

    for section_name, section_data in data.items():
        if section_name.startswith("llm_") and section_name != "llm":
            # Collect LLM provider sections for later processing
            llm_sections.append((section_name, section_data))
        else:
            other_sections[section_name] = section_data

    # Process regular sections first
    for section_name, section_data in other_sections.items():
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

    # Process LLM provider sections
    for section_name, section_data in llm_sections:
        if lines:
            lines.append("")

        # Convert llm_azure_openai to llm.azure_openai format
        provider_name = section_name.replace("llm_", "")
        lines.append(f"[llm.{provider_name}]")

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

    This function attempts to parse a file as TOML to validate its format.

    Args:
        path (Path): Path to configuration file

    Returns:
        bool: True if file is valid TOML

    Example:
        ```python
        from bugninja_cli.utils.initialization import validate_config_file

        if validate_config_file(Path("./bugninja.toml")):
            print("Configuration file is valid")
        else:
            print("Configuration file is invalid")
        ```
    """
    try:
        with open(path, "rb") as f:
            tomli.load(f)
        return True
    except Exception:
        return False


def create_env_template(path: Path) -> None:
    """Create a template .env file.

    This function creates a template `.env.example` file with placeholders
    for sensitive configuration data like API keys.

    Args:
        path (Path): Path to create the .env file

    Example:
        ```python
        from bugninja_cli.utils.initialization import create_env_template

        create_env_template(Path("./.env.example"))
        ```
    """
    env_content = """# Bugninja Sensitive Configuration
# Copy this file to .env and fill in your secret values
# 
# IMPORTANT: This file contains ONLY sensitive data (API keys, passwords, tokens)
# All other configuration is now stored in bugninja.toml

# =============================================================================
# LLM Configuration (Sensitive Data Only)
# =============================================================================

# LLM Provider Selection (set this to choose your provider)
# Options: azure_openai, openai, anthropic, google_gemini, deepseek, ollama
LLM_PROVIDER=azure_openai

# Azure OpenAI Configuration (required if LLM_PROVIDER=azure_openai)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here

# OpenAI Configuration (required if LLM_PROVIDER=openai)
# OPENAI_API_KEY=your-openai-api-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic Configuration (required if LLM_PROVIDER=anthropic)
# ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google Gemini Configuration (required if LLM_PROVIDER=google_gemini)
# GOOGLE_API_KEY=your-google-api-key-here

# DeepSeek Configuration (required if LLM_PROVIDER=deepseek)
# DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Ollama Configuration (optional, defaults to localhost:11434)
# OLLAMA_BASE_URL=http://localhost:11434

# =============================================================================
# Note: All other configuration (logging, paths, browser settings, etc.)
# is now managed in bugninja.toml file for better organization and version control.
# =============================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(env_content)


def create_readme_template(path: Path, project_name: str) -> None:
    """Create a README template for the project.

    This function creates a comprehensive README.md file with project
    documentation, setup instructions, and usage examples.

    Args:
        path (Path): Path to create the README file
        project_name (str): Name of the project

    Example:
        ```python
        from bugninja_cli.utils.initialization import create_readme_template

        create_readme_template(Path("./README.md"), "my-automation-project")
        ```
    """
    readme_content = f"""# {project_name}

This is a Bugninja browser automation project.

## Project Structure

- `bugninja.toml` - Project configuration
- `.env` - Sensitive configuration (API keys, etc.)
- `traversals/` - Recorded browser sessions
- `screenshots/` - Screenshots from automation runs
- `tasks/` - BugninjaTask definitions and descriptions

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
