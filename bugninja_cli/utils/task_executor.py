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
result = await executor.execute_task(task_info)

# Execute multiple tasks in parallel
results = await executor.execute_multiple_tasks(task_infos)
```
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console

if TYPE_CHECKING:
    from bugninja.api import BugninjaTask
    from bugninja.config.video_recording import VideoRecordingConfig
    from bugninja.schemas import TaskExecutionResult, TaskInfo, TaskRunConfig
    from bugninja.schemas.models import BugninjaConfig
    from bugninja.schemas.pipeline import Traversal
    from bugninja_cli.utils.task_manager import TaskManager


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

            from browser_use.browser.profile import (  # type: ignore
                Geolocation,
                ProxySettings,
            )

            from bugninja.api import BugninjaClient
            from bugninja.events import EventPublisherManager
            from bugninja.schemas.models import BugninjaConfig

            # Choose configuration mode based on context:
            # - CLI mode (TOML) when executing a concrete CLI task (TaskInfo provided)
            # - Library mode (env) for in-code TaskSpec usage (no TaskInfo)
            use_cli_mode = task_info is not None

            # Create configuration with task-specific settings if provided
            config = BugninjaConfig(
                headless=self.task_run_config.headless,
                viewport_width=self.task_run_config.viewport_width,
                viewport_height=self.task_run_config.viewport_height,
                user_agent=self.task_run_config.user_agent,
                cli_mode=use_cli_mode,
            )

            # Apply network and location overrides from TaskRunConfig
            if getattr(self.task_run_config, "proxy_server", None):
                try:
                    config.proxy = ProxySettings(server=self.task_run_config.proxy_server)  # type: ignore
                except Exception:
                    config.proxy = None

            if (
                getattr(self.task_run_config, "geolocation_latitude", None) is not None
                and getattr(self.task_run_config, "geolocation_longitude", None) is not None
            ):
                try:
                    config.geolocation = Geolocation(
                        latitude=self.task_run_config.geolocation_latitude,  # type: ignore
                        longitude=self.task_run_config.geolocation_longitude,  # type: ignore
                        accuracy=(self.task_run_config.geolocation_accuracy or 100.0),  # type: ignore
                    )
                except Exception:
                    config.geolocation = None

            # Set task-specific output directory if task_info is provided
            if task_info:
                task_output_dir = self.project_root / "tasks" / task_info.folder_name
                config.output_base_dir = task_output_dir

                # Set correct screenshots directory for CLI mode
                config.screenshots_dir = task_output_dir / "screenshots"
            else:
                # For library-mode (in-code TaskSpec), let BugninjaConfig use its defaults
                # and avoid forcing a CLI-style screenshots directory
                config.screenshots_dir = None

            # Handle video recording if enabled and task_info is provided
            if self.task_run_config.enable_video_recording and task_info:
                try:
                    # Check FFmpeg availability first
                    from bugninja.utils.video_recording_manager import (
                        VideoRecordingManager,
                    )

                    if not VideoRecordingManager.check_ffmpeg_availability():
                        self.logger.warning(
                            "⚠️ FFmpeg is not available. Video recording will be disabled. Please install FFmpeg to enable video recording."
                        )
                        # Disable video recording for this session
                        config.video_recording = None
                    else:
                        # Ensure videos directory exists
                        videos_dir = self._ensure_videos_directory(task_info)

                        # Create video recording configuration
                        video_config = self.task_run_config.get_video_recording_config(
                            str(videos_dir)
                        )
                        if video_config:
                            # Set the video recording configuration directly
                            config.video_recording = video_config
                            self.logger.bugninja_log(
                                f"🎥 Video recording enabled for task: {task_info.name}"
                            )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Video recording setup failed: {e}. Task will continue without video recording."
                    )
                    # Disable video recording for this session
                    config.video_recording = None

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

    # ---------------- Dependency resolution utilities -----------------
    def _resolve_task_by_identifier(
        self, task_identifier: str, task_manager: "TaskManager"
    ) -> "TaskInfo":
        ti = task_manager.get_task_by_name(task_identifier)
        if ti:
            return ti
        ti = task_manager.get_task_by_cuid(task_identifier)
        if ti:
            return ti
        raise ValueError(f"Dependency not found: {task_identifier}")

    def _load_task_config(self, toml_path: Path) -> Dict[str, Any]:
        from bugninja.config.factory import ConfigurationFactory

        return ConfigurationFactory.load_task_config(toml_path)

    def _collect_output_keys(self, task_info: "TaskInfo") -> set[str]:
        cfg = self._load_task_config(task_info.toml_path)
        output = cfg.get("task.output_schema") or {}
        if not isinstance(output, dict):
            return set()
        return set(output.keys())

    def _collect_input_keys(self, task_info: "TaskInfo") -> set[str]:
        cfg = self._load_task_config(task_info.toml_path)
        input_schema = cfg.get("task.input_schema") or {}
        if not isinstance(input_schema, dict):
            return set()
        return set(input_schema.keys())

    def _resolve_dependencies_toposort(
        self, root: "TaskInfo", task_manager: "TaskManager"
    ) -> list["TaskInfo"]:
        # DFS topo with cycle detection
        from collections import defaultdict

        graph: dict[str, list[str]] = defaultdict(list)
        nodes: dict[str, TaskInfo] = {}

        def load_deps(ti: "TaskInfo") -> list[str]:
            cfg = self._load_task_config(ti.toml_path)
            deps = cfg.get("task.dependencies") or []
            return [str(d) for d in deps if isinstance(d, (str, int))]

        # build graph on the fly
        def get_key(ti: "TaskInfo") -> str:
            return ti.folder_name

        stack: list[TaskInfo] = [root]
        visited: set[str] = set()
        while stack:
            cur = stack.pop()
            key = get_key(cur)
            if key in visited:
                continue
            visited.add(key)
            nodes[key] = cur
            for dep_id in load_deps(cur):
                dep_ti = self._resolve_task_by_identifier(dep_id, task_manager)
                graph[get_key(dep_ti)].append(key)  # edge dep -> cur
                stack.append(dep_ti)

        # topo sort
        indeg: dict[str, int] = {k: 0 for k in nodes}
        for u, outs in graph.items():
            for v in outs:
                indeg[v] = indeg.get(v, 0) + 1

        queue = [k for k, d in indeg.items() if d == 0]
        order: list[str] = []
        while queue:
            u = queue.pop()
            order.append(u)
            for v in graph.get(u, []):
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)

        if len(order) != len(nodes):
            raise ValueError("Cyclic dependency detected among tasks")

        # map to TaskInfo and store resolved dependencies
        result = [nodes[k] for k in order]

        # Store resolved dependencies for the root task
        resolved_deps = []
        for ti in result[:-1]:  # all except the last (root) task
            resolved_deps.append({"folder": ti.folder_name, "task_id": ti.task_id})

        # Store in the root task for later use in traversal
        if hasattr(root, "resolved_dependencies"):
            root.resolved_dependencies = resolved_deps

        return result

    def _validate_cross_io(self, task_info: "TaskInfo", parents: list["TaskInfo"]) -> None:
        # union of parents' outputs must be subset of child's inputs
        required_keys: set[str] = set()
        for p in parents:
            required_keys |= self._collect_output_keys(p)
        if not required_keys:
            return
        child_keys = self._collect_input_keys(task_info)
        missing = required_keys - child_keys
        if missing:
            # group by parent for precise diff
            details: dict[str, list[str]] = {}
            for p in parents:
                k = p.folder_name
                need = self._collect_output_keys(p) - child_keys
                if need:
                    details[k] = sorted(list(need))
            raise ValueError(
                f"Input/Output schema mismatch for '{task_info.name}'. Missing keys: {sorted(list(missing))}. Per-parent: {details}"
            )

    def get_latest_traversal_for_task(self, task_info: "TaskInfo") -> Optional[Path]:
        """Return the latest traversal file for a given task, if any.

        Args:
            task_info: Task to look up traversals for

        Returns:
            Optional[Path]: Path to the latest traversal JSON, or None if not found
        """
        traversals_dir = self._ensure_traversals_directory(task_info)
        traversal_files = list(traversals_dir.glob("*.json"))
        if not traversal_files:
            return None
        return max(traversal_files, key=lambda f: f.stat().st_mtime)

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
        """Find traversal file by task name using the latest AI-navigated run.

        Args:
            task_name: Name of the task
            project_root: Root directory of the Bugninja project

        Returns:
            Path: Path to the latest traversal file from ai_navigated_runs

        Raises:
            FileNotFoundError: If task or traversal file not found
            ValueError: If JSON file is malformed
        """
        task_dir: Path = project_root / "tasks" / task_name

        if not task_dir.exists():
            raise FileNotFoundError(f"Task not found: {task_name} (missing {task_dir})")

        try:
            from bugninja_cli.utils.run_history_manager import RunHistoryManager

            # Use RunHistoryManager to get the latest traversal
            history_manager = RunHistoryManager(task_dir)
            traversal_path = history_manager.get_latest_ai_run_traversal()

            if not traversal_path:
                raise FileNotFoundError(f"No AI-navigated runs found in task '{task_name}'")

            if not traversal_path.exists():
                raise FileNotFoundError(f"Traversal file not found: {traversal_path}")

            return traversal_path

        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to read task run history for '{task_name}': {e}")

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

    def _ensure_videos_directory(self, task_info: TaskInfo) -> Path:
        """Ensure videos directory exists for the task.

        Args:
            task_info (TaskInfo): Task information object

        Returns:
            Path: Path to the videos directory
        """
        videos_dir = task_info.task_path / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        return videos_dir

    def _update_video_recording_config(
        self, config: "BugninjaConfig", video_config: "VideoRecordingConfig"
    ) -> None:
        """Update video recording configuration with task-specific settings.

        Args:
            config (BugninjaConfig): The Bugninja configuration to update
            video_config (VideoRecordingConfig): Task-specific video configuration
        """
        # Update all video recording settings
        if config.video_recording:
            config.video_recording.output_dir = video_config.output_dir
            config.video_recording.width = video_config.width
            config.video_recording.height = video_config.height
            config.video_recording.fps = video_config.fps
            config.video_recording.quality = video_config.quality
            config.video_recording.output_format = video_config.output_format
            config.video_recording.codec = video_config.codec
            config.video_recording.preset = video_config.preset
            config.video_recording.crf = video_config.crf
            config.video_recording.bitrate = video_config.bitrate
            config.video_recording.pixel_format = video_config.pixel_format
            config.video_recording.max_queue_size = video_config.max_queue_size

    def _update_task_metadata(
        self, task_info: TaskInfo, result: TaskExecutionResult, run_type: str = "ai_navigated"
    ) -> None:
        """Update task metadata with new run tracking system.

        Args:
            task_info (TaskInfo): Task information object
            result (TaskExecutionResult): Execution result
            run_type (str): Type of run ("ai_navigated" or "replay")
        """
        try:
            from bugninja_cli.utils.run_history_manager import RunHistoryManager

            # Use RunHistoryManager to add the run
            history_manager = RunHistoryManager(task_info.task_path)

            if run_type == "ai_navigated":
                history_manager.add_ai_run(result)
            else:  # replay
                # For replay runs, we need the original traversal ID
                # This should be passed from the caller, but for now we'll use a placeholder
                original_traversal_id = "unknown"  # TODO: Pass this from caller
                healing_enabled = False  # TODO: Pass this from caller
                history_manager.add_replay_run(result, original_traversal_id, healing_enabled)

            self.logger.bugninja_log(
                f"Updated metadata for task '{task_info.name}' with {run_type} run"
            )

            # Create Jira ticket if task failed (non-blocking)
            if not result.success:
                self._create_jira_ticket_for_failure(task_info, result, run_type, history_manager)

        except Exception as e:
            raise ValueError(f"Failed to update task metadata: {e}")

    def _create_jira_ticket_for_failure(
        self,
        task_info: TaskInfo,
        result: TaskExecutionResult,
        run_type: str,
        history_manager: Any,
    ) -> None:
        """Create Jira ticket for failed test case (non-blocking).

        Args:
            task_info (TaskInfo): Task information object
            result (TaskExecutionResult): Execution result
            run_type (str): Type of run ("ai_navigated" or "replay")
            history_manager: RunHistoryManager instance
        """
        from bugninja_cli.utils.jira_integration import JiraIntegration

        JiraIntegration.create_ticket_for_task_failure(
            task_info=task_info,
            result=result,
            run_type=run_type,
            history_manager=history_manager,
        )

    async def replay_traversal(
        self,
        traversal_path: Path,
        enable_healing: bool = False,
        extra_secrets: Optional[Dict[str, Any]] = None,
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

            # Reinitialize client with original browser configuration and video recording settings
            await self._initialize_client_with_traversal_config(traversal_config)

            # Execute replay using BugninjaClient
            console.print(f"🔄 Replaying traversal: {traversal_path.name}")
            result = await self.client.replay_session(
                session=traversal_path, enable_healing=enable_healing, extra_secrets=extra_secrets
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Determine output traversal path
            output_traversal_path = None
            if result.success and result.traversal_file:
                output_traversal_path = result.traversal_file

            # Create execution result
            execution_result = TaskExecutionResult(
                task_info=None,  # No task info for replay
                success=result.success,
                execution_time=execution_time,
                traversal_path=output_traversal_path,
                error_message=str(result.error) if result.error else None,
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
                cli_mode=True,  # Enable CLI mode for TOML configuration
            )

            # Handle video recording configuration if enabled in task
            if self.task_run_config.enable_video_recording:
                try:
                    # Check FFmpeg availability first
                    from bugninja.utils.video_recording_manager import (
                        VideoRecordingManager,
                    )

                    if not VideoRecordingManager.check_ffmpeg_availability():
                        self.logger.warning(
                            "⚠️ FFmpeg is not available. Video recording will be disabled. Please install FFmpeg to enable video recording."
                        )
                    else:
                        # Create video recording configuration
                        from bugninja.config.video_recording import VideoRecordingConfig

                        # Use the same output directory structure as the original task
                        # For replay, we need to determine the original task directory
                        if hasattr(self, "task_info") and self.task_info:
                            # Use the original task directory
                            task_name = self.task_info.folder_name
                            output_base_dir = self.project_root / "tasks" / task_name
                        else:
                            # Fallback to a generic replay directory
                            output_base_dir = self.project_root / "tasks" / "replay"

                        videos_dir = output_base_dir / "videos"
                        videos_dir.mkdir(parents=True, exist_ok=True)

                        video_config = VideoRecordingConfig(
                            output_dir=str(videos_dir),
                            width=self.task_run_config.viewport_width,
                            height=self.task_run_config.viewport_height,
                        )

                        config.video_recording = video_config
                        self.logger.bugninja_log("🎥 Video recording enabled for replay")

                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Video recording setup failed: {e}. Replay will continue without video recording."
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

    async def execute_task(
        self,
        task_info: TaskInfo,
        extra_secrets: Optional[Dict[str, Any]] = None,
    ) -> TaskExecutionResult:
        """Execute a single task.

        Args:
            task_info (TaskInfo): Task information object

        Returns:
            TaskExecutionResult: Execution result
        """
        if not self.client:
            raise RuntimeError("Bugninja client not initialized")

        start_time = datetime.now()
        from bugninja.schemas import TaskExecutionResult

        try:
            # Always initialize client with task-specific configuration
            await self._initialize_client(
                enable_logging=self.enable_logging,
                task_info=task_info,
            )

            # Create BugninjaTask
            task = self._create_bugninja_task(task_info)

            # Execute task
            console.print(f"🔄 Executing task: {task_info.name}")
            result = await self.client.run_task(
                task,
                runtime_inputs=extra_secrets,
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Determine traversal path
            traversal_path = None
            if result.success and result.traversal_file:
                traversal_path = result.traversal_file
            elif result.success:
                # Find the traversal file in the task-specific traversals directory
                traversals_dir = self._ensure_traversals_directory(task_info)
                traversal_files = list(traversals_dir.glob("*.json"))
                if traversal_files:
                    # Get the most recent file
                    traversal_path = max(traversal_files, key=lambda f: f.stat().st_mtime)

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
