"""Task service for managing Bugninja tasks.

This service wraps the existing TaskManager and related utilities from bugninja_cli
to provide task data in formats suitable for the REST API and frontend expectations.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import tomli

from bugninja.schemas.cli_schemas import TaskInfo
from bugninja_cli.utils.task_lookup import get_task_by_identifier
from bugninja_cli.utils.task_manager import TaskManager


class TaskService:
    """Service for managing Bugninja tasks.

    This service provides methods for:
    - Listing all tasks in a project
    - Getting individual task details
    - Transforming task data for API responses
    - Calculating run statistics from traversal files

    Attributes:
        project_root (Path): Root directory of the Bugninja project
        task_manager (TaskManager): Task manager instance from CLI utilities
    """

    def __init__(self, project_root: Path):
        """Initialize TaskService.

        Args:
            project_root (Path): Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.task_manager = TaskManager(project_root)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks in the project.

        Returns:
            List[Dict]: List of task information dictionaries in backend format
        """
        # Get all tasks from TaskManager
        tasks = self.task_manager.list_tasks()

        # Transform to API format
        return [self._transform_task_info(task) for task in tasks]

    def get_task(self, task_identifier: str) -> Optional[Dict[str, Any]]:
        """Get a single task by identifier (name or folder name).

        Args:
            task_identifier (str): Task name, folder name, or CUID

        Returns:
            Optional[Dict]: Task information dictionary, or None if not found
        """
        # Use existing lookup utility from CLI
        task_info = get_task_by_identifier(self.task_manager, task_identifier)

        if not task_info:
            return None

        return self._transform_task_info(task_info)

    def _transform_task_info(self, task_info: TaskInfo) -> Dict[str, Any]:
        """Transform TaskInfo to API response format matching frontend expectations.

        Args:
            task_info (TaskInfo): Task information from TaskManager

        Returns:
            dict: Transformed task data in BackendTestCase format
        """
        # Read TOML file to get task details
        toml_data = self._read_task_toml(task_info.toml_path)
        task_section = toml_data.get("task", {})
        run_config = toml_data.get("run_config", {})
        metadata = toml_data.get("metadata", {})

        # Calculate run statistics
        stats = self._calculate_run_statistics(task_info.task_path)

        # Transform browser configs from TOML
        browser_configs = self._transform_browser_configs(run_config, task_info.folder_name)

        # Get project ID (use project folder name)
        project_id = self.project_root.name

        # Parse created/updated timestamps
        created_at = metadata.get("created_date", datetime.now().isoformat())
        # Use file modification time for updated_at
        toml_stat = task_info.toml_path.stat()
        updated_at = datetime.fromtimestamp(toml_stat.st_mtime).isoformat()

        return {
            # Core identifiers
            "id": task_info.folder_name,
            "project_id": project_id,
            # Timestamps
            "created_at": created_at,
            "updated_at": updated_at,
            # Task content
            "test_name": task_info.name,
            "test_description": task_section.get("description", ""),
            "test_goal": task_section.get("description", ""),  # Use description as goal
            # Configuration
            "url_routes": task_section.get("start_url", ""),
            "url_route": task_section.get("start_url", ""),  # Duplicate for compatibility
            "extra_rules": task_section.get("extra_instructions", []),
            "allowed_domains": task_section.get("allowed_domains", []),
            "priority": task_section.get("priority", "medium"),
            "category": task_section.get("category", None),
            # Related entities
            "browser_configs": browser_configs,
            "secrets": [],  # TODO: Implement secrets extraction
            "document": None,  # Not used in CLI mode
            # Run statistics
            "total_runs": stats["total_runs"],
            "passed_runs": stats["passed_runs"],
            "failed_runs": stats["failed_runs"],
            "pending_runs": stats["pending_runs"],
            "success_rate": stats["success_rate"],
            "last_run_at": stats["last_run_at"],
        }

    def _read_task_toml(self, toml_path: Path) -> Dict[str, Any]:
        """Read and parse task TOML file.

        Args:
            toml_path (Path): Path to task TOML file

        Returns:
            dict: Parsed TOML data
        """
        with open(toml_path, "rb") as f:
            return tomli.load(f)

    def _calculate_run_statistics(self, task_path: Path) -> Dict[str, Any]:
        """Calculate run statistics from traversal files.

        Args:
            task_path (Path): Path to task directory

        Returns:
            dict: Statistics including total_runs, passed_runs, failed_runs, success_rate, last_run_at
        """
        traversals_dir = task_path / "traversals"

        if not traversals_dir.exists():
            return {
                "total_runs": 0,
                "passed_runs": 0,
                "failed_runs": 0,
                "pending_runs": 0,
                "success_rate": 0.0,
                "last_run_at": None,
            }

        # Get all traversal JSON files
        traversal_files = list(traversals_dir.glob("traverse_*.json"))
        total_runs = len(traversal_files)

        if total_runs == 0:
            return {
                "total_runs": 0,
                "passed_runs": 0,
                "failed_runs": 0,
                "pending_runs": 0,
                "success_rate": 0.0,
                "last_run_at": None,
            }

        # Analyze each traversal file
        passed_runs = 0
        failed_runs = 0
        last_run_time = None

        for traversal_file in traversal_files:
            try:
                with open(traversal_file, "r") as f:
                    import json

                    traversal_data = json.load(f)

                # Check if test completed successfully
                # A successful run has actions with "done" action
                actions = traversal_data.get("actions", {})
                has_done = any(
                    action_data.get("action", {}).get("done") is not None
                    for action_data in actions.values()
                )

                if has_done:
                    passed_runs += 1
                else:
                    # If no done action, consider it failed
                    failed_runs += 1

                # Get file modification time for last_run_at
                file_stat = traversal_file.stat()
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                if last_run_time is None or file_time > last_run_time:
                    last_run_time = file_time

            except Exception:
                # If file is corrupted or unreadable, count as failed
                failed_runs += 1

        # Calculate success rate
        success_rate = (passed_runs / total_runs * 100) if total_runs > 0 else 0.0

        return {
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "pending_runs": 0,  # No way to determine pending from files
            "success_rate": round(success_rate, 2),
            "last_run_at": last_run_time.isoformat() if last_run_time else None,
        }

    def _transform_browser_configs(
        self, run_config: Dict[str, Any], task_name: str
    ) -> List[Dict[str, Any]]:
        """Transform browser config from TOML to BackendBrowserConfig format.

        Args:
            run_config (Dict): Run configuration from TOML
            task_name (str): Task name for generating config ID

        Returns:
            List[Dict]: List of browser configurations in backend format
        """
        # Generate a config from the TOML run_config section
        viewport_width = run_config.get("viewport_width", 1920)
        viewport_height = run_config.get("viewport_height", 1080)
        user_agent = run_config.get("user_agent", "")

        # Create a single browser config based on TOML settings
        browser_config = {
            "id": f"{task_name}_default",  # Generate stable ID
            "project_id": self.project_root.name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "browser_config": {
                "browser_channel": "chromium",  # Default
                "user_agent": user_agent,
                "viewport": {
                    "width": viewport_width,
                    "height": viewport_height,
                },
                "device_scale_factor": 1.0,
                "color_scheme": "light",
                "accept_downloads": True,
                "client_certificates": [],
                "extra_http_headers": {},
                "java_script_enabled": True,
                "timeout": 30000,
                "allowed_domains": [],
                "geolocation": None,
            },
        }

        return [browser_config]
