"""Execution service for running Bugninja tasks in the background.

This service handles task execution using the existing PipelineExecutor,
running tasks asynchronously and managing run IDs.
"""

from pathlib import Path
from typing import Optional

from cuid2 import Cuid

from bugninja_cli.utils.pipeline_executor import PipelineExecutor
from bugninja_cli.utils.task_lookup import get_task_by_identifier
from bugninja_cli.utils.task_manager import TaskManager


class ExecutionService:
    """Service for executing Bugninja tasks in the background.

    This service provides methods for:
    - Starting task execution asynchronously
    - Generating run IDs
    - Tracking execution status

    Attributes:
        project_root (Path): Root directory of the Bugninja project
    """

    def __init__(self, project_root: Path):
        """Initialize ExecutionService.

        Args:
            project_root (Path): Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.task_manager = TaskManager(project_root)

    def generate_run_id(self) -> str:
        """Generate a unique run ID using CUID.

        Returns:
            str: Unique run identifier
        """
        return Cuid().generate()

    async def execute_task(self, task_identifier: str) -> None:
        """Execute a task asynchronously.

        This method starts task execution using PipelineExecutor. The task
        runs in the background and writes results incrementally to a traversal
        file. The library generates its own run_id which can be extracted from
        the traversal filename.

        Args:
            task_identifier (str): Task name, folder name, or CUID

        Raises:
            ValueError: If task not found
        """
        # Get task info
        task_info = get_task_by_identifier(self.task_manager, task_identifier)
        if not task_info:
            raise ValueError(f"Task '{task_identifier}' not found")

        # Execute task using PipelineExecutor
        # The library will generate its own run_id
        pipeline_executor = PipelineExecutor(self.project_root)
        await pipeline_executor.execute_with_dependencies(task_info, self.task_manager)

    def get_task_identifier_by_name(self, task_name: str) -> Optional[str]:
        """Get task identifier by task name.

        Args:
            task_name (str): Task name

        Returns:
            Optional[str]: Task folder name if found, None otherwise
        """
        task_info = get_task_by_identifier(self.task_manager, task_name)
        if task_info:
            return task_info.folder_name
        return None
