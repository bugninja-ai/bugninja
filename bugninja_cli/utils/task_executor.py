"""
Task execution utilities for Bugninja CLI commands.

This module provides **comprehensive utilities** for:
- task execution using Bugninja API
- environment variable parsing
- task metadata management
- traversal storage and organization

## Key Components

1. **TaskExecutor** - Main class for task execution operations
2. **TaskExecutionResult** - Data class for execution results
3. **Environment parsing utilities** - Parse .env files for secrets
4. **Traversal management** - Store and organize traversal files

## Usage Examples

```python
from bugninja_cli.utils.task_executor import TaskExecutor

# Create task executor
executor = TaskExecutor(project_root)

# Execute single task
result = await executor.execute_task(task_info, headless=True)

# Execute multiple tasks in parallel
results = await executor.execute_multiple_tasks(task_infos, headless=True)
```
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console

from .task_manager import TaskInfo

if TYPE_CHECKING:
    from bugninja.api import BugninjaTask
    from bugninja.api.models import BugninjaTaskResult
    from bugninja.schemas.pipeline import Traversal


console = Console()


class TaskExecutionResult:
    """Result of a task execution operation.

    This class represents the outcome of a task execution, including
    success status, execution time, and file paths.

    Attributes:
        task_info (TaskInfo): Information about the executed task
        success (bool): Whether the task executed successfully
        execution_time (float): Execution time in seconds
        traversal_path (Optional[Path]): Path to the generated traversal file
        error_message (Optional[str]): Error message if execution failed
        result (Optional[BugninjaTaskResult]): Raw Bugninja API result
    """

    def __init__(
        self,
        task_info: TaskInfo,
        success: bool,
        execution_time: float,
        traversal_path: Optional[Path] = None,
        error_message: Optional[str] = None,
        result: Optional["BugninjaTaskResult"] = None,
    ):
        self.task_info = task_info
        self.success = success
        self.execution_time = execution_time
        self.traversal_path = traversal_path
        self.error_message = error_message
        self.result = result


class TaskExecutor:
    """Executor for Bugninja tasks using the API.

    This class provides comprehensive task execution capabilities including
    single task execution, parallel task execution, and proper resource
    management using the Bugninja API.

    Attributes:
        project_root (Path): Root directory of the Bugninja project
        client (Optional[BugninjaClient]): Bugninja client instance
    """

    def __init__(self, project_root: Path, headless: bool = True, enable_logging: bool = False):
        """Initialize the TaskExecutor with project root.

        Args:
            project_root (Path): Root directory of the Bugninja project
            headless (bool): Whether to run in headless mode (default: True)
            enable_logging (bool): Whether to enable Bugninja logging (default: False)
        """
        self.project_root = project_root
        self.headless = headless
        self.enable_logging = enable_logging
        from bugninja.api import BugninjaClient
        from bugninja.utils.logging_config import logger as bugninja_logger

        self.client: Optional[BugninjaClient] = None

        self.logger = bugninja_logger

    async def __aenter__(self) -> "TaskExecutor":
        """Async context manager entry."""
        await self._initialize_client(headless=self.headless, enable_logging=self.enable_logging)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type:ignore
        """Async context manager exit with cleanup."""
        await self.cleanup()

    async def _initialize_client(self, headless: bool = True, enable_logging: bool = False) -> None:
        """Initialize the Bugninja client.

        Args:
            headless (bool): Whether to run in headless mode
            enable_logging (bool): Whether to enable Bugninja logging
        """
        try:
            # Set logging environment variable before client initialization

            os.environ["BUGNINJA_LOGGING_ENABLED"] = str(enable_logging).lower()

            from bugninja.api import BugninjaClient
            from bugninja.api.models import BugninjaConfig
            from bugninja.events import EventPublisherManager

            # Create configuration with headless mode
            config = BugninjaConfig(headless=headless)

            # Create event manager for progress tracking (empty list for no publishers)
            event_manager = EventPublisherManager([])

            # Initialize client
            self.client = BugninjaClient(config=config, event_manager=event_manager)

            self.logger.bugninja_log(
                f"Bugninja client initialized successfully (headless: {headless}, logging: {enable_logging})"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Bugninja client: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            try:
                await self.client.cleanup()
                self.logger.bugninja_log("Bugninja client cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error during client cleanup: {e}")

    def _parse_env_file(self, env_path: Path) -> Dict[str, Any]:
        """Parse environment variables from .env file.

        Args:
            env_path (Path): Path to the .env file

        Returns:
            Dict[str, Any]: Dictionary of environment variables

        Raises:
            FileNotFoundError: If .env file doesn't exist
            ValueError: If .env file is malformed
        """
        if not env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {env_path}")

        secrets: Dict[str, Any] = {}

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        secrets[key] = value
                    else:
                        self.logger.warning(f"Invalid line {line_num} in {env_path}: {line}")

        except Exception as e:
            raise ValueError(f"Failed to parse environment file {env_path}: {e}")

        return secrets

    def _read_task_description(self, description_path: Path) -> str:
        """Read task description from markdown file.

        Args:
            description_path (Path): Path to the task.md file

        Returns:
            str: Task description content

        Raises:
            FileNotFoundError: If task.md file doesn't exist
            ValueError: If task.md file is empty or unreadable
        """
        if not description_path.exists():
            raise FileNotFoundError(f"Task description file not found: {description_path}")

        try:
            with open(description_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                raise ValueError(f"Task description file is empty: {description_path}")

            return content
        except Exception as e:
            raise ValueError(f"Failed to read task description from {description_path}: {e}")

    def _read_task_metadata(self, metadata_path: Path) -> Dict[str, Any]:
        """Read task metadata from JSON file.

        Args:
            metadata_path (Path): Path to the metadata.json file

        Returns:
            Dict[str, Any]: Task metadata

        Raises:
            FileNotFoundError: If metadata.json file doesn't exist
            ValueError: If metadata.json file is malformed
        """
        if not metadata_path.exists():
            raise FileNotFoundError(f"Task metadata file not found: {metadata_path}")

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata: Dict[str, Any] = json.load(f)
            return metadata
        except Exception as e:
            raise ValueError(f"Failed to read task metadata from {metadata_path}: {e}")

    def _create_bugninja_task(self, task_info: TaskInfo) -> "BugninjaTask":
        """Create a BugninjaTask from task information.

        Args:
            task_info (TaskInfo): Task information object

        Returns:
            BugninjaTask: Configured Bugninja task

        Raises:
            ValueError: If task configuration is invalid
        """
        try:
            # Read task description
            description = self._read_task_description(task_info.description_path)

            # Parse environment variables
            secrets = self._parse_env_file(task_info.env_path)

            # Read metadata for allowed domains
            metadata = self._read_task_metadata(task_info.metadata_path)
            allowed_domains = metadata.get("allowed_domains", [])
            from bugninja.api import BugninjaTask

            # Create BugninjaTask
            task = BugninjaTask(
                description=description,
                secrets=secrets,
                allowed_domains=allowed_domains if allowed_domains else None,
            )

            self.logger.bugninja_log(f"Created BugninjaTask for '{task_info.name}'")
            return task

        except Exception as e:
            raise ValueError(f"Failed to create BugninjaTask for '{task_info.name}': {e}")

    def _ensure_traversals_directory(self, task_info: TaskInfo) -> Path:
        """Ensure traversals directory exists for the task.

        Args:
            task_info (TaskInfo): Task information object

        Returns:
            Path: Path to the traversals directory
        """
        traversals_dir = task_info.task_path / "traversals"
        traversals_dir.mkdir(exist_ok=True)
        return traversals_dir

    def _update_task_metadata(self, task_info: TaskInfo, result: TaskExecutionResult) -> None:
        """Update task metadata with execution results.

        Args:
            task_info (TaskInfo): Task information object
            result (TaskExecutionResult): Execution result
        """
        try:
            # Read current metadata
            metadata = self._read_task_metadata(task_info.metadata_path)

            # Update with execution results
            metadata["latest_run_path"] = (
                str(result.traversal_path) if result.traversal_path else None
            )
            metadata["latest_run_status"] = "success" if result.success else "failed"
            metadata["latest_run_timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Write updated metadata
            with open(task_info.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.bugninja_log(f"Updated metadata for task '{task_info.name}'")

        except Exception as e:
            self.logger.error(f"Failed to update metadata for task '{task_info.name}': {e}")

    async def execute_task(self, task_info: TaskInfo, headless: bool = True) -> TaskExecutionResult:
        """Execute a single task.

        Args:
            task_info (TaskInfo): Task information object
            headless (bool): Whether to run in headless mode

        Returns:
            TaskExecutionResult: Execution result
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")

        start_time = datetime.now()

        try:
            # Create BugninjaTask
            task = self._create_bugninja_task(task_info)

            # Ensure traversals directory exists
            traversals_dir = self._ensure_traversals_directory(task_info)

            # Execute task
            console.print(f"🔄 Executing task: {task_info.name}")
            result = await self.client.run_task(task)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Determine traversal path
            traversal_path = None
            if result.success and result.traversal_file:
                traversal_path = result.traversal_file
            elif result.success:
                # Create traversal filename based on timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                traversal_filename = f"run_{timestamp}.json"
                traversal_path = traversals_dir / traversal_filename

                # Save traversal if available
                if result.traversal:
                    with open(traversal_path, "w", encoding="utf-8") as f:
                        json.dump(result.traversal.model_dump(), f, indent=2, ensure_ascii=False)

            # Create execution result
            execution_result = TaskExecutionResult(
                task_info=task_info,
                success=result.success,
                execution_time=execution_time,
                traversal_path=traversal_path,
                error_message=str(result.error) if result.error else None,
                result=result,
            )

            # Update task metadata
            self._update_task_metadata(task_info, execution_result)

            if result.success:
                console.print(f"✅ Task '{task_info.name}' completed successfully")
            else:
                console.print(
                    f"❌ Task '{task_info.name}' failed: {execution_result.error_message}"
                )

            return execution_result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = str(e)

            console.print(f"❌ Task '{task_info.name}' failed: {error_message}")

            # Create failed execution result
            execution_result = TaskExecutionResult(
                task_info=task_info,
                success=False,
                execution_time=execution_time,
                error_message=error_message,
            )

            # Update task metadata
            self._update_task_metadata(task_info, execution_result)

            return execution_result

    async def execute_multiple_tasks(
        self, task_infos: List[TaskInfo], headless: bool = True
    ) -> List[TaskExecutionResult]:
        """Execute multiple tasks in parallel.

        Args:
            task_infos (List[TaskInfo]): List of task information objects
            headless (bool): Whether to run in headless mode

        Returns:
            List[TaskExecutionResult]: List of execution results
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")

        try:
            # Create BugninjaTask objects
            tasks: List[Path | Traversal | BugninjaTask] = []
            for task_info in task_infos:
                try:
                    task = self._create_bugninja_task(task_info)
                    tasks.append(task)
                except Exception as e:
                    console.print(f"❌ Failed to create task '{task_info.name}': {e}")
                    # Continue with other tasks

            if not tasks:
                console.print("❌ No valid tasks to execute")
                return []

            # Execute tasks in parallel
            console.print(f"🔄 Executing {len(tasks)} tasks in parallel")
            bulk_result = await self.client.parallel_run_mixed(
                executions=tasks,
                max_concurrent=len(tasks),
                enable_healing=True,
            )

            # Process results
            results = []
            for i, (task_info, task_result) in enumerate(
                zip(task_infos, bulk_result.individual_results)
            ):
                # Ensure traversals directory exists
                traversals_dir = self._ensure_traversals_directory(task_info)

                # Determine traversal path
                traversal_path = None
                if task_result.success and task_result.traversal_file:
                    traversal_path = task_result.traversal_file
                elif task_result.success:
                    # Create traversal filename based on timestamp and task index
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    traversal_filename = f"run_{timestamp}_task{i+1}.json"
                    traversal_path = traversals_dir / traversal_filename

                    # Save traversal if available
                    if task_result.traversal:
                        with open(traversal_path, "w", encoding="utf-8") as f:
                            json.dump(
                                task_result.traversal.model_dump(), f, indent=2, ensure_ascii=False
                            )

                # Create execution result
                execution_result = TaskExecutionResult(
                    task_info=task_info,
                    success=task_result.success,
                    execution_time=task_result.execution_time,
                    traversal_path=traversal_path,
                    error_message=str(task_result.error) if task_result.error else None,
                    result=task_result,
                )

                # Update task metadata
                self._update_task_metadata(task_info, execution_result)

                results.append(execution_result)

                if task_result.success:
                    console.print(f"✅ Task '{task_info.name}' completed successfully")
                else:
                    console.print(
                        f"❌ Task '{task_info.name}' failed: {execution_result.error_message}"
                    )

            return results

        except Exception as e:
            console.print(f"❌ Failed to execute multiple tasks: {e}")
            return []
