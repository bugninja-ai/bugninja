"""Project service for reading and managing Bugninja project configuration.

This service wraps access to the `bugninja.toml` configuration file and provides
project information in a format suitable for the REST API.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import tomli


class ProjectService:
    """Service for managing Bugninja project configuration.

    This service provides methods for:
    - Reading project configuration from `bugninja.toml`
    - Validating project structure
    - Returning project information for API responses

    Attributes:
        project_root (Path): Root directory of the Bugninja project
    """

    def __init__(self, project_root: Path):
        """Initialize ProjectService.

        Args:
            project_root (Path): Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.config_file = project_root / "bugninja.toml"

    def get_project_info(self) -> Dict[str, Any]:
        """Get project information from bugninja.toml.

        Returns:
            dict: Project information containing:
                - id: Project root directory name
                - name: Project name from config
                - default_start_url: Default starting URL (if configured)
                - created_at: Config file creation time
                - updated_at: Config file last modified time
                - tasks_dir: Path to tasks directory
                - config: Full configuration data

        Raises:
            FileNotFoundError: If bugninja.toml does not exist
            Exception: If TOML parsing fails
        """
        if not self.config_file.exists():
            raise FileNotFoundError(
                f"bugninja.toml not found in {self.project_root}. "
                "Is this a valid Bugninja project?"
            )

        # Read and parse TOML file
        with open(self.config_file, "rb") as f:
            config = tomli.load(f)

        from datetime import datetime

        # Get file stats
        stats = self.config_file.stat()

        # Extract project info
        project_name = config.get("project", {}).get("name", self.project_root.name)
        default_start_url = config.get("project", {}).get("default_start_url", "")

        # Convert timestamps to ISO strings (frontend expects this format)
        created_at = datetime.fromtimestamp(stats.st_birthtime).isoformat()
        updated_at = datetime.fromtimestamp(stats.st_mtime).isoformat()

        return {
            "id": self.project_root.name,  # Use folder name as ID
            "name": project_name,
            "default_start_url": default_start_url,
            "created_at": created_at,  # ISO string
            "updated_at": updated_at,  # ISO string
        }

    def update_project_info(
        self, name: Optional[str] = None, default_start_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update project information in bugninja.toml.

        Args:
            name (Optional[str]): New project name
            default_start_url (Optional[str]): New default start URL

        Returns:
            dict: Updated project information

        Raises:
            FileNotFoundError: If bugninja.toml does not exist
        """
        import tomli_w

        if not self.config_file.exists():
            raise FileNotFoundError(f"bugninja.toml not found in {self.project_root}")

        # Read current config
        with open(self.config_file, "rb") as f:
            config = tomli.load(f)

        # Update fields if provided
        if "project" not in config:
            config["project"] = {}

        if name is not None:
            config["project"]["name"] = name

        if default_start_url is not None:
            config["project"]["default_start_url"] = default_start_url

        # Write back to file
        with open(self.config_file, "wb") as f:
            tomli_w.dump(config, f)

        # Return updated info
        return self.get_project_info()

    def validate_project(self) -> bool:
        """Validate that this is a proper Bugninja project.

        Returns:
            bool: True if valid project structure exists

        Checks:
            - bugninja.toml exists
            - tasks/ directory exists
        """
        if not self.config_file.exists():
            return False

        tasks_dir = self.project_root / "tasks"
        if not tasks_dir.exists() or not tasks_dir.is_dir():
            return False

        return True
