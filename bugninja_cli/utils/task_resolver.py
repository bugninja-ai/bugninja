"""
Task resolver implementation for CLI TOML-based dependency resolution.

This module provides the CLI implementation of the TaskResolver protocol,
enabling BugninjaPipeline to work seamlessly with TOML-based task dependencies.
"""

from __future__ import annotations

from typing import List

import tomli

from bugninja.api import BugninjaTask
from bugninja.api.bugninja_pipeline import TaskRef
from bugninja_cli.utils.task_lookup import get_task_by_identifier
from bugninja_cli.utils.task_manager import TaskManager


class CLITaskResolver:
    """CLI implementation of TaskResolver for TOML-based dependency resolution.

    This class bridges the gap between CLI task management and BugninjaPipeline
    by providing methods to resolve task references and extract dependencies
    from TOML configuration files.

    Attributes:
        task_manager (TaskManager): Task manager instance for task resolution
    """

    def __init__(self, task_manager: TaskManager):
        """Initialize CLITaskResolver.

        Args:
            task_manager: Task manager instance for resolving task identifiers
        """
        self.task_manager = task_manager

    def resolve_task_ref(self, task_ref: TaskRef) -> BugninjaTask:
        """Resolve TaskRef to BugninjaTask using task_manager.

        Args:
            task_ref: Reference to a task by identifier

        Returns:
            BugninjaTask: Resolved task instance with config path

        Raises:
            ValueError: If task cannot be resolved by identifier
        """
        task_info = get_task_by_identifier(self.task_manager, task_ref.identifier)
        if not task_info:
            raise ValueError(f"Could not resolve task by identifier: {task_ref.identifier}")

        return BugninjaTask(task_config_path=task_info.toml_path)

    def get_task_dependencies(self, identifier: str) -> List[str]:
        """Get dependency identifiers for a task from TOML file.

        Args:
            identifier: Task identifier (folder name or CUID)

        Returns:
            List[str]: List of dependency identifiers from TOML configuration
        """
        task_info = get_task_by_identifier(self.task_manager, identifier)
        if not task_info:
            return []

        try:
            with open(task_info.toml_path, "rb") as f:
                task_config = tomli.load(f)
            dep_ids = task_config.get("task", {}).get("dependencies", [])
            return [str(dep_id) for dep_id in dep_ids]
        except Exception:
            return []
