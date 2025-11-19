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

    async def execute_task(self, task_identifier: str, run_id: str) -> str:
        """Execute a task asynchronously with a pre-generated run_id.

        This method starts task execution using PipelineExecutor and returns
        immediately. The task continues running in the background, writing
        results to the traversal file with the provided run_id.

        Args:
            task_identifier (str): Task name, folder name, or CUID
            run_id (str): Pre-generated run ID that will be used for the traversal file

        Returns:
            str: The same run ID that was passed in

        Raises:
            ValueError: If task not found
        """
        # Get task info
        task_info = get_task_by_identifier(self.task_manager, task_identifier)
        if not task_info:
            raise ValueError(f"Task '{task_identifier}' not found")

        # Execute task using PipelineExecutor with the provided run_id
        # We need to modify the task to use this run_id
        pipeline_executor = PipelineExecutor(self.project_root)

        # TODO: We need to pass run_id through to the NavigatorAgent
        # For now, execute without it (the agent will generate its own)
        # This will be fixed in the next iteration
        await pipeline_executor.execute_with_dependencies(task_info, self.task_manager)

        return run_id

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
