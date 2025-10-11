"""
Task management utilities for Bugninja CLI commands.

This module provides **comprehensive utilities** for:
- task creation and validation
- task metadata management
- task file structure creation
- task uniqueness validation

## Key Components

1. **TaskManager** - Main class for task operations
2. **TaskInfo** - Data class for task information
3. **Task creation utilities** - Template generation and file creation

## Usage Examples

```python
from bugninja_cli.utils.task_manager import TaskManager

# Create task manager for current project
task_manager = TaskManager(project_root)

# Create a new task
task_id = task_manager.create_task("Login Flow")

# Check if task exists
if task_manager.task_exists("Login Flow"):
    print("Task already exists")
```
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import tomli
from cuid2 import Cuid as CUID
from rich.console import Console

if TYPE_CHECKING:
    from bugninja.schemas import TaskInfo
    from bugninja.schemas.test_case_creation import TestCaseCreationOutput
    from bugninja.schemas.test_case_io import TestCaseSchema

console = Console()


def name_to_snake_case(name: str) -> str:
    """Convert task name to snake_case folder name.

    This function converts a human-readable task name to a valid filesystem
    folder name using snake_case convention.

    Args:
        name (str): Human-readable task name

    Returns:
        str: Snake case folder name

    Example:
        ```python
        name_to_snake_case("Login Flow")  # Returns "login_flow"
        name_to_snake_case("User Registration v2.0")  # Returns "user_registration_v2_0"
        name_to_snake_case("API Test (Production)")  # Returns "api_test_production"
        ```
    """
    # Normalize unicode characters
    name = unicodedata.normalize("NFKD", name)

    # Convert to lowercase
    name = name.lower()

    # Replace spaces, hyphens, dots with underscores
    name = re.sub(r"[\s\-\.]+", "_", name)

    # Remove special characters except alphanumeric and underscores
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Replace multiple underscores with single underscore
    name = re.sub(r"_+", "_", name)

    # Remove leading and trailing underscores
    name = name.strip("_")

    return name


def validate_folder_name(folder_name: str) -> bool:
    """Validate if folder name is valid for filesystem.

    Args:
        folder_name (str): Folder name to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not folder_name or not folder_name.strip():
        return False

    # Check length
    if len(folder_name) > 128:
        return False

    # Check for reserved names (Windows)
    reserved_names = {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }

    if folder_name.lower() in reserved_names:
        return False

    # Check for valid characters
    if not re.match(r"^[a-z0-9_]+$", folder_name):
        return False

    return True


class TaskManager:
    """Manager for Bugninja task operations.

    This class provides comprehensive task management capabilities including
    task creation, validation, and metadata handling. It ensures proper
    file structure and maintains task uniqueness within a project.

    Attributes:
        project_root (Path): Root directory of the Bugninja project
        tasks_dir (Path): Directory containing all tasks
    """

    def __init__(self, project_root: Path):
        """Initialize the TaskManager with project root.

        Args:
            project_root (Path): Root directory of the Bugninja project

        Raises:
            ValueError: If project_root is not a valid Bugninja project
        """
        self.project_root = project_root
        self.tasks_dir = project_root / "tasks"

        # Validate that we have a tasks directory
        if not self.tasks_dir.exists():
            raise ValueError(f"Tasks directory not found: {self.tasks_dir}")

        if not self.tasks_dir.is_dir():
            raise ValueError(f"Tasks path is not a directory: {self.tasks_dir}")

    def create_task(self, name: str, dependencies: Optional[List[str]] = None) -> str:
        """Create a new task with the given name.

        This method creates a complete task structure including:
        - Task directory with snake_case name
        - Task description file (task.md)
        - Task metadata file (metadata.json)
        - Task environment file (.env)

        Args:
            name (str): Human-readable name for the task
            dependencies (Optional[List[str]]): Optional list of dependency testcase names

        Returns:
            str: CUID2 identifier of the created task

        Raises:
            ValueError: If task name is invalid or already exists
            OSError: If file system operations fail
        """
        # Validate task name
        if not self.validate_task_name(name):
            raise ValueError(f"Invalid task name: {name}")

        # Convert name to snake_case folder name
        folder_name = name_to_snake_case(name)

        # Check if task already exists (case-insensitive)
        if self.task_exists(name):
            existing_path = self.get_existing_task_path(name)
            raise ValueError(f"Task '{name}' already exists at: {existing_path}")

        # Resolve dependencies to canonical folder names
        resolved_deps: List[str] = []
        if dependencies:
            seen = set()
            for dep in dependencies:
                dep = dep.strip()
                if not dep:
                    continue
                # prevent self-dependency by name or folder
                if dep.lower() == name.lower() or name_to_snake_case(dep) == folder_name:
                    raise ValueError("A task cannot depend on itself")

                # Resolve to folder name if task exists
                dep_path = self.get_existing_task_path(dep)
                if dep_path is None:
                    # Also try direct folder name path under tasks
                    candidate = self.tasks_dir / name_to_snake_case(dep)
                    if candidate.exists() and candidate.is_dir():
                        dep_path = candidate

                if dep_path is None:
                    raise ValueError(f"Dependency not found: {dep}")

                dep_folder = dep_path.name
                if dep_folder not in seen:
                    seen.add(dep_folder)
                    resolved_deps.append(dep_folder)

        # Generate unique task ID
        task_id = CUID().generate()
        task_dir = self.tasks_dir / folder_name

        try:
            # Create task directory
            task_dir.mkdir(parents=False, exist_ok=False)

            # Create task files
            self._create_task_toml(task_dir, name, task_id, resolved_deps)

            from bugninja.utils.logging_config import logger

            logger.info(f"Created task '{name}' with ID: {task_id} in folder: {folder_name}")
            return task_id

        except Exception as e:
            # Clean up on failure
            if task_dir.exists():
                import shutil

                shutil.rmtree(task_dir)
            raise OSError(f"Failed to create task: {e}")

    def task_exists(self, name: str) -> bool:
        """Check if a task with the given name already exists.

        Args:
            name (str): Task name to check

        Returns:
            bool: True if task exists, False otherwise
        """
        return self.get_existing_task_path(name) is not None

    def get_existing_task_path(self, name: str) -> Optional[Path]:
        """Get the path of an existing task by name.

        Args:
            name (str): Task name to find

        Returns:
            Optional[Path]: Path to existing task directory if found, None otherwise
        """
        folder_name = name_to_snake_case(name)
        task_dir = self.tasks_dir / folder_name

        if task_dir.exists() and task_dir.is_dir():
            return task_dir

        return None

    def get_task_by_cuid(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information by CUID.

        Args:
            task_id (str): CUID of the task to find

        Returns:
            Optional[TaskInfo]: Task information if found, None otherwise
        """
        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            toml_file = task_dir / f"task_{task_dir.name}.toml"
            if not toml_file.exists():
                continue

            try:

                with open(toml_file, "rb") as f:
                    config = tomli.load(f)

                metadata_section = config.get("metadata", {})
                if metadata_section.get("task_id") == task_id:
                    from bugninja.schemas import TaskInfo

                    task_section = config.get("task", {})
                    return TaskInfo(
                        name=task_section.get("name", "Unknown"),
                        task_id=task_id,
                        folder_name=task_dir.name,
                        task_path=task_dir,
                        toml_path=toml_file,
                    )
            except (tomli.TOMLDecodeError, KeyError, FileNotFoundError):
                continue

        return None

    def get_task_by_name(self, name: str) -> Optional[TaskInfo]:
        """Get task information by name.

        Args:
            name (str): Task name to find

        Returns:
            Optional[TaskInfo]: Task information if found, None otherwise
        """
        folder_name = name_to_snake_case(name)
        task_dir = self.tasks_dir / folder_name

        if not task_dir.exists() or not task_dir.is_dir():
            return None

        toml_file = task_dir / f"task_{folder_name}.toml"
        if not toml_file.exists():
            return None

        try:

            with open(toml_file, "rb") as f:
                config = tomli.load(f)

            task_section = config.get("task", {})
            metadata_section = config.get("metadata", {})
            from bugninja.schemas import TaskInfo

            return TaskInfo(
                name=task_section.get("name", "Unknown"),
                task_id=metadata_section.get("task_id", "Unknown"),
                folder_name=folder_name,
                task_path=task_dir,
                toml_path=toml_file,
            )
        except (tomli.TOMLDecodeError, KeyError, FileNotFoundError):
            return None

    def list_tasks(self) -> List[TaskInfo]:
        """List all available tasks in the project.

        Returns:
            List[TaskInfo]: List of task information objects
        """
        tasks = []

        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            toml_file = task_dir / f"task_{task_dir.name}.toml"
            if not toml_file.exists():
                continue

            try:

                with open(toml_file, "rb") as f:
                    config = tomli.load(f)

                task_section = config.get("task", {})
                metadata_section = config.get("metadata", {})
                from bugninja.schemas import TaskInfo

                task_info = TaskInfo(
                    name=task_section.get("name", "Unknown"),
                    task_id=metadata_section.get("task_id", "Unknown"),
                    folder_name=task_dir.name,
                    task_path=task_dir,
                    toml_path=toml_file,
                )
                tasks.append(task_info)
            except (tomli.TOMLDecodeError, KeyError, FileNotFoundError):
                continue

        return tasks

    def validate_task_name(self, name: str) -> bool:
        """Validate a task name.

        Args:
            name (str): Task name to validate

        Returns:
            bool: True if name is valid, False otherwise
        """
        if not name or not name.strip():
            return False

        # Remove leading/trailing whitespace
        name = name.strip()

        # Check for reasonable length (128 chars max)
        if len(name) < 1 or len(name) > 128:
            return False

        # Check if the resulting folder name would be valid
        folder_name = name_to_snake_case(name)
        if not validate_folder_name(folder_name):
            return False

        return True

    def create_imported_task(
        self,
        creation_output: "TestCaseCreationOutput",
        source_files: list[str],
        schema: Optional["TestCaseSchema"] = None,
    ) -> str:
        """Create a new task from imported test case generation.

        This method creates a complete task structure from AI-generated test case
        content, including proper metadata for imported tasks.

        Args:
            creation_output (TestCaseCreationOutput): Generated test case content
            source_files (list[str]): List of source file paths used for generation

        Returns:
            str: CUID2 identifier of the created task

        Raises:
            ValueError: If task name is invalid or already exists
            OSError: If file system operations fail
        """
        # Validate task name
        if not self.validate_task_name(creation_output.task_name):
            raise ValueError(f"Invalid task name: {creation_output.task_name}")

        # Convert name to snake_case folder name
        folder_name = name_to_snake_case(creation_output.task_name)

        # Check if task already exists (case-insensitive)
        if self.task_exists(creation_output.task_name):
            existing_path = self.get_existing_task_path(creation_output.task_name)
            raise ValueError(
                f"Task '{creation_output.task_name}' already exists at: {existing_path}"
            )

        # Generate unique task ID
        task_id = CUID().generate()
        task_dir = self.tasks_dir / folder_name

        try:
            # Create task directory
            task_dir.mkdir(parents=False, exist_ok=False)

            # Create task files
            self._create_imported_task_toml(
                task_dir, creation_output, task_id, source_files, schema
            )

            from bugninja.utils.logging_config import logger

            logger.info(
                f"Created imported task '{creation_output.task_name}' with ID: {task_id} in folder: {folder_name}"
            )
            return task_id

        except Exception as e:
            # Clean up on failure
            if task_dir.exists():
                import shutil

                shutil.rmtree(task_dir)
            raise OSError(f"Failed to create imported task: {e}")

    def _create_task_toml(
        self, task_dir: Path, name: str, task_id: str, dependencies: Optional[List[str]] = None
    ) -> None:
        """Create the task TOML configuration file.

        Args:
            task_dir (Path): Task directory path
            name (str): Task name
            task_id (str): Task CUID2 identifier
            dependencies (Optional[List[str]]): Resolved dependency folder names
        """
        toml_file = task_dir / f"task_{name_to_snake_case(name)}.toml"
        content = self._get_task_toml_template(name, task_id, dependencies or [])

        with open(toml_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _get_task_toml_template(self, name: str, task_id: str, dependencies: List[str]) -> str:
        """Get the task TOML template.

        Args:
            name (str): Task name
            task_id (str): Task CUID2 identifier
            dependencies (List[str]): Resolved dependency folder names

        Returns:
            str: TOML template content
        """
        # Format dependencies list as TOML array
        if not dependencies:
            deps_line = (
                "[]  # Optional: List of task folder names or CUIDs that this task depends on"
            )
        else:
            quoted = ", ".join(f'"{d}"' for d in dependencies)
            deps_line = f"[{quoted}]"

        return f"""# Task Configuration for: {name}
# This file contains task-specific configuration including description and run settings
# Run history is stored separately in run_history.json

[task]
name = "{name}"
start_url = "https://example.com"  # REQUIRED: URL where the browser session should start
description = "Describe your task here..."
extra_instructions = [
    "Add specific instructions for this task",
    "Each instruction should be on a separate line"
]
allowed_domains = []  # Optional: List of allowed domains for web tasks
dependencies = {deps_line}

# I/O Schema Configuration (Optional)
# Uncomment and configure if you need data extraction capabilities
[task.io_schema]
# input schema is defined as a dictionary of input field names to descriptions
# input_schema.USER_EMAIL = "test@example.com"

# output schema is defined as a dictionary of output field names to descriptions
# output_schema.USER_ID = "ID of the registered user"

[secrets]
# Task-specific secrets - these will be passed to the NavigatorAgent
# SECRET_KEY = "secret_value"
# USERNAME = "your_username"
# PASSWORD = "your_password"
# API_KEY = "your_api_key"

[run_config]
# CLI-specific runtime configuration
viewport_width = 1920
viewport_height = 1080
user_agent = ""
wait_between_actions = 1.0
enable_vision = true
enable_healing = true
headless = false
enable_video_recording = true

[metadata]
task_id = "{task_id}"
created_date = "{datetime.now(UTC).isoformat()}Z"
creation_type = "manually_added"
"""

    def _create_imported_task_toml(
        self,
        task_dir: Path,
        creation_output: "TestCaseCreationOutput",
        task_id: str,
        source_files: list[str],
        schema: Optional["TestCaseSchema"] = None,
    ) -> None:
        """Create the imported task TOML configuration file.

        Args:
            task_dir (Path): Task directory path
            creation_output (TestCaseCreationOutput): Generated test case content
            task_id (str): Task CUID2 identifier
            source_files (list[str]): List of source file paths
        """
        toml_file = task_dir / f"task_{name_to_snake_case(creation_output.task_name)}.toml"
        content = self._get_imported_task_toml_template(
            creation_output, task_id, source_files, schema
        )

        with open(toml_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _get_imported_task_toml_template(
        self,
        creation_output: "TestCaseCreationOutput",
        task_id: str,
        source_files: list[str],
        schema: Optional["TestCaseSchema"] = None,
    ) -> str:
        """Get the imported task TOML template.

        Args:
            creation_output (TestCaseCreationOutput): Generated test case content
            task_id (str): Task CUID2 identifier
            source_files (list[str]): List of source file paths

        Returns:
            str: TOML template content
        """
        # Format secrets section
        secrets_section = ""
        if creation_output.secrets:
            secrets_lines = []
            for key, value in creation_output.secrets.items():
                secrets_lines.append(f'{key} = "{value}"')
            secrets_section = "\n".join(secrets_lines)
        else:
            secrets_section = "# No secrets found in source files"

        # Format extra instructions
        instructions_lines = []
        for instruction in creation_output.extra_instructions:
            instructions_lines.append(f'    "{instruction}"')
        instructions_section = "[\n" + ",\n".join(instructions_lines) + "\n]"

        # Format source files
        source_files_lines = []
        for source_file in source_files:
            source_files_lines.append(f'    "{source_file}"')
        source_files_section = "[\n" + ",\n".join(source_files_lines) + "\n]"

        # Format unified schema section
        schema_section = ""
        if schema:
            schema_lines = []
            if schema.input_schema:
                input_lines = []
                for key, value in schema.input_schema.items():
                    if isinstance(value, str):
                        input_lines.append(f'    "{key}" = "{value}"')
                    else:
                        input_lines.append(f'    "{key}" = {value}')
                schema_lines.append("input_schema = {\n" + ",\n".join(input_lines) + "\n}")

            if schema.output_schema:
                output_lines = []
                for key, value in schema.output_schema.items():
                    output_lines.append(f'    "{key}" = "{value}"')
                schema_lines.append("output_schema = {\n" + ",\n".join(output_lines) + "\n}")

            if schema_lines:
                schema_section = "\n[task.schema]\n" + "\n".join(schema_lines)

        return f"""# Task Configuration for: {creation_output.task_name}
# This file contains task-specific configuration including description and run settings
# Run history is stored separately in run_history.json
# Generated from imported files: {', '.join(source_files)}

[task]
name = "{creation_output.task_name}"
description = "{creation_output.description}"
extra_instructions = {instructions_section}
allowed_domains = []  # Optional: List of allowed domains for web tasks{schema_section}

[secrets]
{secrets_section}

[run_config]
# CLI-specific runtime configuration
viewport_width = 1920
viewport_height = 1080
user_agent = ""
wait_between_actions = 1.0
enable_vision = true
enable_healing = true
headless = false
enable_video_recording = true

[metadata]
task_id = "{task_id}"
created_date = "{datetime.now(UTC).isoformat()}Z"
creation_type = "import_generated"
source_files = {source_files_section}
"""
