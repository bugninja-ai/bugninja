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

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console

if TYPE_CHECKING:
    from bugninja.api import BugninjaTask
    from bugninja.schemas import TaskExecutionResult, TaskInfo, TaskRunConfig
    from bugninja.schemas.pipeline import Traversal


console = Console()


class TaskExecutor:
    """Executor for Bugninja tasks using the API.

    This class provides comprehensive task execution capabilities including
    single task execution, parallel task execution, and proper resource
    management using the Bugninja API.

    Attributes:
        project_root (Path): Root directory of the Bugninja project
        client (Optional[BugninjaClient]): Bugninja client instance
    """

    def __init__(
        self,
        task_run_config: TaskRunConfig,
        project_root: Path,
        enable_logging: bool = False,
    ):
        """Initialize the TaskExecutor with project root.

        Args:
            project_root (Path): Root directory of the Bugninja project
            headless (bool): Whether to run in headless mode (default: True)
            enable_logging (bool): Whether to enable Bugninja logging (default: False)
        """
        self.project_root = project_root
        self.enable_logging = enable_logging
        self.task_run_config = task_run_config
        from bugninja.api import BugninjaClient
        from bugninja.utils.logging_config import logger as bugninja_logger

        self.client: Optional[BugninjaClient] = None

        self.logger = bugninja_logger

    async def __aenter__(self) -> "TaskExecutor":
        """Async context manager entry."""
        await self._initialize_client(enable_logging=self.enable_logging)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type:ignore
        """Async context manager exit with cleanup."""
        await self.cleanup()

    async def _initialize_client(
        self,
        enable_logging: bool = False,
        task_info: Optional["TaskInfo"] = None,
    ) -> None:
        """Initialize the Bugninja client.

        Args:
            enable_logging (bool): Whether to enable Bugninja logging
            task_info (Optional[TaskInfo]): Task information for task-specific configuration
        """

        try:
            # Set logging environment variable before client initialization

            os.environ["BUGNINJA_LOGGING_ENABLED"] = str(enable_logging).lower()

            from bugninja.api import BugninjaClient
            from bugninja.events import EventPublisherManager
            from bugninja.schemas.models import BugninjaConfig

            # Create configuration with task-specific settings if provided
            config = BugninjaConfig(
                headless=self.task_run_config.headless,
                viewport_width=self.task_run_config.viewport_width,
                viewport_height=self.task_run_config.viewport_height,
                user_agent=self.task_run_config.user_agent,
            )

            # Set task-specific output directory if task_info is provided
            if task_info:
                task_output_dir = self.project_root / "tasks" / task_info.folder_name
                config.output_base_dir = task_output_dir

            # Create event manager for progress tracking (empty list for no publishers)
            event_manager = EventPublisherManager([])

            # Initialize client
            self.client = BugninjaClient(config=config, event_manager=event_manager)

            self.logger.bugninja_log(
                f"✅ Bugninja client initialized successfully (headless: {config.headless}, logging: {enable_logging})"
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
            from bugninja.api import BugninjaTask

            # Create BugninjaTask using config file path
            task = BugninjaTask(task_config_path=task_info.toml_path)

            self.logger.bugninja_log(
                f"🎫 Created BugninjaTask for '{task_info.name}' from config file: {task_info.toml_path}"
            )
            return task

        except Exception as e:
            raise ValueError(f"Failed to create BugninjaTask for '{task_info.name}': {e}")

    @staticmethod
    def _load_task_run_config(toml_path: Path) -> TaskRunConfig:
        """Load task run configuration from TOML file.

        Args:
            toml_path: Path to the task TOML file

        Returns:
            TaskRunConfig: Configuration for task execution
        """
        from bugninja.schemas import TaskRunConfig

        try:
            from bugninja.config.factory import ConfigurationFactory

            # Load task configuration from TOML
            task_config = ConfigurationFactory.load_task_config(toml_path)

            # Create TaskRunConfig from TOML data
            return TaskRunConfig.from_toml_config(task_config)

        except Exception:
            # Return default configuration if loading fails
            return TaskRunConfig()

    @staticmethod
    def find_traversal_by_id(traversal_id: str, project_root: Path) -> Path:
        """Find traversal file by run_id.

        Args:
            traversal_id: The run_id part of the traversal filename
            project_root: Root directory of the Bugninja project

        Returns:
            Path: Path to the traversal file

        Raises:
            FileNotFoundError: If no traversal file matches the ID
            ValueError: If multiple files match the ID
        """
        traversals_dir = project_root / "traversals"
        if not traversals_dir.exists():
            raise FileNotFoundError(f"Traversals directory not found: {traversals_dir}")

        # Find files matching the pattern traverse_*_{traversal_id}.json
        matching_files = list(traversals_dir.glob(f"traverse_*_{traversal_id}.json"))

        if not matching_files:
            raise FileNotFoundError(f"No traversal file found with ID: {traversal_id}")

        if len(matching_files) > 1:
            file_names = [f.name for f in matching_files]
            raise ValueError(f"Multiple traversal files match ID '{traversal_id}': {file_names}")

        return matching_files[0]

    @staticmethod
    def find_traversal_by_task_name(task_name: str, project_root: Path) -> Path:
        """Find traversal file by task name using latest_run_path.

        Args:
            task_name: Name of the task
            project_root: Root directory of the Bugninja project

        Returns:
            Path: Path to the traversal file from latest_run_path

        Raises:
            FileNotFoundError: If task or traversal file not found
            ValueError: If TOML file is malformed
        """
        task_toml_path: Path = project_root / "tasks" / task_name / f"task_{task_name}.toml"

        if not task_toml_path.exists():
            raise FileNotFoundError(f"Task not found: {task_name} (missing {task_toml_path})")

        try:
            import tomli

            with open(task_toml_path, "rb") as f:
                config = tomli.load(f)

            latest_run_path = config.get("metadata", {}).get("latest_run_path")
            if not latest_run_path:
                raise FileNotFoundError(f"No latest_run_path found in task '{task_name}'")

            traversal_path: Path = project_root / latest_run_path
            if not traversal_path.exists():
                raise FileNotFoundError(f"Traversal file not found: {traversal_path}")

            return traversal_path

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to read task configuration for '{task_name}': {e}")

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
            # Read current TOML configuration
            import tomli

            with open(task_info.toml_path, "rb") as f:
                config = tomli.load(f)

            # Update metadata section with execution results
            if "metadata" not in config:
                config["metadata"] = {}

            config["metadata"]["latest_run_path"] = (
                str(result.traversal_path) if result.traversal_path else ""
            )
            config["metadata"]["latest_run_status"] = "success" if result.success else "failed"
            config["metadata"]["latest_run_timestamp"] = datetime.now(UTC).isoformat()

            # Write updated TOML configuration
            import tomli_w

            with open(task_info.toml_path, "wb") as f:
                tomli_w.dump(config, f)

            self.logger.bugninja_log(f"Updated metadata for task '{task_info.name}'")

        except Exception as e:
            self.logger.error(f"Failed to update metadata for task '{task_info.name}': {e}")

    async def replay_traversal(
        self, traversal_path: Path, enable_healing: bool = False
    ) -> TaskExecutionResult:
        """Replay a recorded traversal.

        Args:
            traversal_path: Path to the traversal file to replay
            enable_healing: Whether to enable healing during replay

        Returns:
            TaskExecutionResult: Replay execution result
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")

        start_time = datetime.now()
        from bugninja.schemas import TaskExecutionResult

        try:
            # Load traversal file to get original browser configuration
            traversal_config = self._load_traversal_config(traversal_path)

            # Reinitialize client with original browser configuration
            await self._initialize_client_with_traversal_config(traversal_config)

            # Execute replay using BugninjaClient
            console.print(f"🔄 Replaying traversal: {traversal_path.name}")
            result = await self.client.replay_session(
                session=traversal_path, enable_healing=enable_healing
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Determine output traversal path
            output_traversal_path = None
            if result.success and result.traversal_file:
                output_traversal_path = result.traversal_file
            elif result.success:
                # Create new traversal filename for replay results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                replay_filename = f"replay_{timestamp}_{traversal_path.stem}.json"
                output_traversal_path = self.project_root / "traversals" / replay_filename

                # Save traversal if available
                if result.traversal:
                    with open(output_traversal_path, "w", encoding="utf-8") as f:
                        json.dump(result.traversal.model_dump(), f, indent=2, ensure_ascii=False)

            # Create execution result
            execution_result = TaskExecutionResult(
                task_info=None,  # No task info for replay
                success=result.success,
                execution_time=execution_time,
                traversal_path=output_traversal_path,
                error_message=result.error.message if result.error else None,
                result=result,
            )

            # Log result
            if result.success:
                console.print(f"✅ Traversal replayed successfully in {execution_time:.2f}s")
                if output_traversal_path:
                    console.print(f"📁 Replay saved to: {output_traversal_path}")
            else:
                console.print(f"❌ Traversal replay failed: {result.error}")

            return execution_result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Traversal replay failed: {str(e)}"

            console.print(f"❌ {error_msg}")

            return TaskExecutionResult(
                task_info=None,
                success=False,
                execution_time=execution_time,
                traversal_path=None,
                error_message=error_msg,
            )

    def _load_traversal_config(self, traversal_path: Path) -> Dict[str, Any]:
        """Load browser configuration from traversal file.

        Args:
            traversal_path: Path to the traversal file

        Returns:
            Dict containing browser configuration from traversal
        """
        try:
            with open(traversal_path, "r", encoding="utf-8") as f:
                traversal_data = json.load(f)

            browser_config: Dict[str, Any] = traversal_data.get("browser_config", {})
            if not browser_config:
                raise ValueError("No browser_config found in traversal file")

            return browser_config

        except Exception as e:
            raise ValueError(f"Failed to load traversal configuration from {traversal_path}: {e}")

    async def _initialize_client_with_traversal_config(
        self, browser_config: Dict[str, Any]
    ) -> None:
        """Initialize Bugninja client with configuration from traversal file.

        Args:
            browser_config: Browser configuration from traversal file
        """
        try:
            from bugninja.api import BugninjaClient
            from bugninja.events import EventPublisherManager
            from bugninja.schemas.models import BugninjaConfig

            # Create BugninjaConfig from traversal browser_config
            config = BugninjaConfig(
                headless=browser_config.get("headless", False),
                viewport_width=browser_config.get("viewport", {}).get("width", 1920),
                viewport_height=browser_config.get("viewport", {}).get("height", 1080),
                user_agent=browser_config.get("user_agent"),
            )

            # Create event manager for progress tracking
            event_manager = EventPublisherManager([])

            # Initialize client
            self.client = BugninjaClient(config=config, event_manager=event_manager)

            self.logger.bugninja_log(
                f"Bugninja client initialized for replay (headless: {config.headless}, "
                f"viewport: {config.viewport_width}x{config.viewport_height})"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Bugninja client for replay: {e}")
            raise

    async def execute_task(self, task_info: TaskInfo) -> TaskExecutionResult:
        """Execute a single task.

        Args:
            task_info (TaskInfo): Task information object
            headless (bool): Whether to run in headless mode (overrides TOML setting)

        Returns:
            TaskExecutionResult: Execution result
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")

        start_time = datetime.now()
        from bugninja.schemas import TaskExecutionResult

        try:

            # Reinitialize client with task-specific configuration
            await self._initialize_client(
                enable_logging=self.enable_logging,
                task_info=task_info,
            )

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
                traversal_filename = f"traverse_{timestamp}.json"
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

    async def execute_multiple_tasks(self, task_infos: List[TaskInfo]) -> List[TaskExecutionResult]:
        """Execute multiple tasks in parallel.

        Args:
            task_infos (List[TaskInfo]): List of task information objects
            headless (bool): Whether to run in headless mode

        Returns:
            List[TaskExecutionResult]: List of execution results
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")
        from bugninja.schemas import TaskExecutionResult

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
                    traversal_filename = f"traverse_{timestamp}_task{i+1}.json"
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
