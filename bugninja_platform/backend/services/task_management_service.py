"""Task management service for creating, updating, and deleting test cases.

This service handles CRUD operations on task TOML files and their associated
directories in the file-based project structure.
"""

import shutil
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional

import toml
from cuid2 import Cuid


class TaskManagementService:
    """Service for managing test case CRUD operations.

    This service provides methods for:
    - Creating new tasks with TOML configuration
    - Updating existing task configuration
    - Deleting tasks and their associated data
    - Validating task data

    Attributes:
        project_root (Path): Root directory of the Bugninja project
    """

    def __init__(self, project_root: Path):
        """Initialize TaskManagementService.

        Args:
            project_root (Path): Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.tasks_dir = project_root / "tasks"

    def create_task(
        self,
        test_name: str,
        test_description: str,
        test_goal: str,
        url_route: str,
        extra_rules: list[str],
        allowed_domains: list[str],
        priority: str = "medium",
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task with TOML configuration file.

        This method creates a new task folder with a TOML configuration file
        following the standard Bugninja task structure. It also creates
        subdirectories for screenshots, traversals, and videos.

        Args:
            test_name (str): Name of the test case (used for folder and file naming)
            test_description (str): Detailed description of the test
            test_goal (str): Goal/objective of the test
            url_route (str): Starting URL for the test
            extra_rules (list[str]): Additional instructions for the test
            allowed_domains (list[str]): List of allowed domains
            priority (str): Test priority (low, medium, high, critical)
            category (Optional[str]): Test category

        Returns:
            Dict[str, Any]: Task information including folder path and task ID

        Raises:
            ValueError: If task with same name already exists
            IOError: If failed to create task files
        """
        # Sanitize test name for folder name (replace spaces, special chars)
        folder_name = test_name.replace(" ", "_").lower()
        folder_name = "".join(c for c in folder_name if c.isalnum() or c == "_")

        # Check if task already exists
        task_folder = self.tasks_dir / folder_name
        if task_folder.exists():
            raise ValueError(f"Task with name '{test_name}' already exists")

        # Generate unique task ID
        task_id = Cuid().generate()

        # Create task folder structure
        task_folder.mkdir(parents=True, exist_ok=True)
        (task_folder / "screenshots").mkdir(exist_ok=True)
        (task_folder / "traversals").mkdir(exist_ok=True)
        (task_folder / "videos").mkdir(exist_ok=True)

        # Create TOML configuration
        toml_data = {
            "task": {
                "name": folder_name,
                "start_url": url_route,
                "description": test_description,
                "goal": test_goal,
                "extra_instructions": extra_rules,
                "allowed_domains": allowed_domains,
                "dependencies": [],
                "priority": priority,
            },
            "run_config": {
                "viewport_width": 1920,
                "viewport_height": 1080,
                "user_agent": "",
                "wait_between_actions": 1.0,
                "enable_vision": True,
                "enable_healing": True,
                "headless": False,
                "enable_video_recording": True,
            },
            "metadata": {
                "task_id": task_id,
                "created_date": datetime.now(UTC).isoformat() + "Z",
                "creation_type": "web_ui",
            },
        }

        # Add category if provided
        if category:
            toml_data["task"]["category"] = category

        # Write TOML file
        toml_file = task_folder / f"task_{folder_name}.toml"
        with open(toml_file, "w") as f:
            toml.dump(toml_data, f)

        return {
            "task_id": task_id,
            "folder_name": folder_name,
            "toml_path": str(toml_file),
            "created_at": toml_data["metadata"]["created_date"],
        }

    def update_task(
        self,
        task_identifier: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing task's TOML configuration.

        This method updates specific fields in the task's TOML file while
        preserving other configuration. It supports updating task details,
        run configuration, and metadata.

        Args:
            task_identifier (str): Task name, folder name, or CUID
            updates (Dict[str, Any]): Dictionary of fields to update

        Returns:
            Dict[str, Any]: Updated task information

        Raises:
            ValueError: If task not found
            IOError: If failed to update task file
        """
        # Find task TOML file
        from bugninja_cli.utils.task_manager import TaskManager
        from bugninja_cli.utils.task_lookup import get_task_by_identifier

        task_manager = TaskManager(self.project_root)
        task_info = get_task_by_identifier(task_manager, task_identifier)

        if not task_info:
            raise ValueError(f"Task '{task_identifier}' not found")

        # Read existing TOML
        toml_path = task_info.toml_path
        with open(toml_path, "r") as f:
            toml_data = toml.load(f)

        # Update fields
        field_mapping = {
            "test_name": ("task", "name"),
            "test_description": ("task", "description"),
            "test_goal": ("task", "goal"),
            "url_route": ("task", "start_url"),
            "extra_rules": ("task", "extra_instructions"),
            "allowed_domains": ("task", "allowed_domains"),
            "priority": ("task", "priority"),
            "category": ("task", "category"),
        }

        for api_field, (section, toml_field) in field_mapping.items():
            if api_field in updates:
                if section not in toml_data:
                    toml_data[section] = {}
                toml_data[section][toml_field] = updates[api_field]

        # Write updated TOML
        with open(toml_path, "w") as f:
            toml.dump(toml_data, f)

        return {
            "task_id": toml_data["metadata"]["task_id"],
            "folder_name": task_info.folder_name,
            "toml_path": str(toml_path),
            "updated": True,
        }

    def delete_task(self, task_identifier: str) -> Dict[str, Any]:
        """Delete a task and all its associated data.

        This method removes the entire task folder including:
        - TOML configuration file
        - Traversal files
        - Screenshots
        - Videos
        - Run history

        Args:
            task_identifier (str): Task name, folder name, or CUID

        Returns:
            Dict[str, Any]: Deletion confirmation with deleted folder info

        Raises:
            ValueError: If task not found
            IOError: If failed to delete task folder
        """
        # Find task
        from bugninja_cli.utils.task_manager import TaskManager
        from bugninja_cli.utils.task_lookup import get_task_by_identifier

        task_manager = TaskManager(self.project_root)
        task_info = get_task_by_identifier(task_manager, task_identifier)

        if not task_info:
            raise ValueError(f"Task '{task_identifier}' not found")

        # Delete entire task folder
        task_folder = self.tasks_dir / task_info.folder_name
        if task_folder.exists():
            shutil.rmtree(task_folder)

        return {
            "message": f"Successfully deleted test case '{task_info.task_id}'",
            "folder_name": task_info.folder_name,
            "task_id": task_info.task_id,
        }

