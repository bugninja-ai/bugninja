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

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cuid2 import Cuid as CUID
from rich.console import Console

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


class TaskInfo:
    """Information about a Bugninja task.

    This class represents the metadata and structure of a Bugninja task,
    including its location, metadata, and file paths.

    Attributes:
        name (str): Human-readable task name
        task_id (str): Unique CUID2 identifier for the task
        folder_name (str): Snake case folder name
        task_path (Path): Path to the task directory
        metadata_path (Path): Path to the task metadata file
        description_path (Path): Path to the task description file
        env_path (Path): Path to the task environment file
    """

    def __init__(
        self,
        name: str,
        task_id: str,
        folder_name: str,
        task_path: Path,
        metadata_path: Path,
        description_path: Path,
        env_path: Path,
    ):
        self.name = name
        self.task_id = task_id
        self.folder_name = folder_name
        self.task_path = task_path
        self.metadata_path = metadata_path
        self.description_path = description_path
        self.env_path = env_path


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

    def create_task(self, name: str) -> str:
        """Create a new task with the given name.

        This method creates a complete task structure including:
        - Task directory with snake_case name
        - Task description file (task.md)
        - Task metadata file (metadata.json)
        - Task environment file (.env)

        Args:
            name (str): Human-readable name for the task

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

        # Generate unique task ID
        task_id = CUID().generate()
        task_dir = self.tasks_dir / folder_name

        try:
            # Create task directory
            task_dir.mkdir(parents=False, exist_ok=False)

            # Create task files
            self._create_task_description(task_dir, name)
            self._create_task_metadata(task_dir, name, task_id)
            self._create_task_env(task_dir)

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

            metadata_file = task_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    if metadata.get("task_identifier") == task_id:
                        return TaskInfo(
                            name=metadata.get("task_name", "Unknown"),
                            task_id=task_id,
                            folder_name=task_dir.name,
                            task_path=task_dir,
                            metadata_path=metadata_file,
                            description_path=task_dir / "task.md",
                            env_path=task_dir / ".env",
                        )
            except (json.JSONDecodeError, KeyError):
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

        metadata_file = task_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                return TaskInfo(
                    name=metadata.get("task_name", "Unknown"),
                    task_id=metadata.get("task_identifier", "Unknown"),
                    folder_name=folder_name,
                    task_path=task_dir,
                    metadata_path=metadata_file,
                    description_path=task_dir / "task.md",
                    env_path=task_dir / ".env",
                )
        except (json.JSONDecodeError, KeyError):
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

            metadata_file = task_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                task_info = TaskInfo(
                    name=metadata.get("task_name", "Unknown"),
                    task_id=metadata.get("task_identifier", "Unknown"),
                    folder_name=task_dir.name,
                    task_path=task_dir,
                    metadata_path=metadata_file,
                    description_path=task_dir / "task.md",
                    env_path=task_dir / ".env",
                )
                tasks.append(task_info)
            except (json.JSONDecodeError, KeyError):
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

    def _create_task_description(self, task_dir: Path, name: str) -> None:
        """Create the task description file.

        Args:
            task_dir (Path): Task directory path
            name (str): Task name
        """
        description_file = task_dir / "task.md"
        content = self._get_task_markdown_template(name)

        with open(description_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _create_task_metadata(self, task_dir: Path, name: str, task_id: str) -> None:
        """Create the task metadata file.

        Args:
            task_dir (Path): Task directory path
            name (str): Task name
            task_id (str): Task CUID2 identifier
        """
        metadata_file = task_dir / "metadata.json"
        metadata = self._get_task_metadata_template(name, task_id)

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _create_task_env(self, task_dir: Path) -> None:
        """Create the task environment file.

        Args:
            task_dir (Path): Task directory path
        """
        env_file = task_dir / ".env"
        content = self._get_task_env_template()

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _get_task_markdown_template(self, name: str) -> str:
        """Get the task markdown template.

        Args:
            name (str): Task name

        Returns:
            str: Markdown template content
        """
        return f"""# {name}

Describe your task here...

## Task Description

Add a detailed description of what this task should accomplish.

## Expected Behavior

Describe the expected outcome of this task.

## Notes

Add any additional notes or requirements here.
"""

    def _get_task_metadata_template(self, name: str, task_id: str) -> Dict[str, Any]:
        """Get the task metadata template.

        Args:
            name (str): Task name
            task_id (str): Task CUID2 identifier

        Returns:
            Dict[str, Any]: Metadata template dictionary
        """
        return {
            "task_name": name,
            "task_identifier": task_id,
            "created_date": datetime.utcnow().isoformat() + "Z",
            "allowed_domains": [],
            "latest_run_path": None,
            "latest_run_status": None,
            "priority": "medium",
        }

    def _get_task_env_template(self) -> str:
        """Get the task environment template.

        Returns:
            str: Environment template content
        """
        return """SECRET_KEY=secret_value

# Add your task-specific secrets here
# Example:
# USERNAME=your_username
# PASSWORD=your_password
# API_KEY=your_api_key
"""
