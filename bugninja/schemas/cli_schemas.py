from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bugninja.config.video_recording import VideoRecordingConfig

from .models import BugninjaTaskResult


class TaskInfo(BaseModel):
    """Information about a Bugninja task.

    This class represents the metadata and structure of a Bugninja task,
    including its location, configuration, and file paths.

    Attributes:
        name (str): Human-readable task name
        task_id (str): Unique CUID2 identifier for the task
        folder_name (str): Snake case folder name
        task_path (Path): Path to the task directory
        toml_path (Path): Path to the task TOML configuration file
    """

    name: str = Field(description="Human-readable task name")
    task_id: str = Field(description="Unique CUID2 identifier for the task")
    folder_name: str = Field(description="Snake case folder name")
    task_path: Path = Field(description="Path to the task directory")
    toml_path: Path = Field(description="Path to the task TOML configuration file")


class TaskRunConfig(BaseModel):
    """CLI-specific configuration for task execution.

    This class handles runtime configuration settings that are specific to the CLI
    execution environment, such as browser viewport, user agent, and execution mode.
    These settings are loaded from the [run_config] section of task TOML files.
    """

    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    wait_between_actions: float = Field(
        default=1.0, description="Wait time between actions (in seconds)"
    )
    enable_vision: bool = Field(default=True, description="Enable vision capabilities")
    enable_healing: bool = Field(default=True, description="Enable healing capabilities")
    headless: bool = Field(default=False, description="Run browser in headless mode")
    enable_video_recording: bool = Field(
        default=False, description="Enable video recording for this task"
    )

    # Network and location (per-task overrides)
    proxy_server: Optional[str] = Field(
        default=None, description="Proxy server URL (e.g. http://host:port or socks5://host:port)"
    )

    geolocation_latitude: Optional[float] = Field(default=None, description="Geolocation latitude")
    geolocation_longitude: Optional[float] = Field(
        default=None, description="Geolocation longitude"
    )
    geolocation_accuracy: Optional[float] = Field(
        default=None, description="Geolocation accuracy in meters"
    )

    @classmethod
    def from_toml_config(cls, config: Dict[str, Any]) -> "TaskRunConfig":
        """Create TaskRunConfig from TOML configuration data.

        Args:
            config: Flattened TOML configuration data

        Returns:
            TaskRunConfig instance with values from TOML or defaults
        """
        return cls(
            viewport_width=config.get("run_config.viewport_width", 1920),
            viewport_height=config.get("run_config.viewport_height", 1080),
            user_agent=config.get("run_config.user_agent"),
            wait_between_actions=config.get("run_config.wait_between_actions", 1.0),
            enable_vision=config.get("run_config.enable_vision", True),
            enable_healing=config.get("run_config.enable_healing", True),
            headless=config.get("run_config.headless", False),
            enable_video_recording=config.get("run_config.enable_video_recording", False),
            proxy_server=config.get("run_config.proxy.server"),
            geolocation_latitude=config.get("run_config.geolocation.latitude"),
            geolocation_longitude=config.get("run_config.geolocation.longitude"),
            geolocation_accuracy=config.get("run_config.geolocation.accuracy"),
        )

    def get_video_recording_config(self, output_dir: str) -> Optional["VideoRecordingConfig"]:
        """Get video recording configuration if enabled.

        Args:
            output_dir: Directory where video files should be saved

        Returns:
            VideoRecordingConfig if video recording is enabled, None otherwise
        """
        if not self.enable_video_recording:
            return None

        from bugninja.config.video_recording import VideoRecordingConfig

        return VideoRecordingConfig(
            output_dir=output_dir,
            width=self.viewport_width,
            height=self.viewport_height,
        )


class TaskExecutionResult(BaseModel):
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

    task_info: Optional[TaskInfo] = Field(
        default=None, description="Information about the executed task"
    )
    success: bool = Field(default=False, description="Whether the task executed successfully")
    execution_time: float = Field(description="Execution time in seconds")
    traversal_path: Optional[Path] = Field(
        default=None, description="Path to the generated traversal file"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    result: Optional["BugninjaTaskResult"] = Field(
        default=None, description="Raw Bugninja API result"
    )
    run_id: Optional[str] = Field(default=None, description="Unique identifier of the executed run")

    class Config:
        """Pydantic configuration for TaskExecutionResult model."""

        arbitrary_types_allowed = True


class RunEntry(BaseModel):
    """Base model for task run entries.

    This class represents a single execution of a task, whether it's an AI-navigated
    run or a replay run. It contains all the essential information about the execution.

    Attributes:
        run_id (str): Unique identifier for this run
        timestamp (str): ISO timestamp when the run was executed
        status (str): Execution status ("success" or "failed")
        traversal_path (str): Path to the generated traversal file
        execution_time (float): Execution time in seconds
        error_message (Optional[str]): Error message if execution failed
    """

    run_id: str = Field(description="Unique identifier for this run")
    timestamp: str = Field(description="ISO timestamp when the run was executed")
    status: str = Field(description="Execution status (success or failed)")
    traversal_path: str = Field(description="Path to the generated traversal file")
    execution_time: float = Field(description="Execution time in seconds")
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )


class AINavigatedRun(RunEntry):
    """AI-navigated run entry.

    This represents a run where the AI agent navigated and executed the task
    from scratch, creating a new traversal.
    """

    pass


class ReplayRun(RunEntry):
    """Replay run entry.

    This represents a run where an existing traversal was replayed, potentially
    with healing enabled.

    Attributes:
        original_traversal_id (str): ID of the original traversal that was replayed
        healing_enabled (bool): Whether healing was enabled during replay
    """

    original_traversal_id: str = Field(description="ID of the original traversal that was replayed")
    healing_enabled: bool = Field(
        default=False, description="Whether healing was enabled during replay"
    )


class TaskRunSummary(BaseModel):
    """Summary statistics for task runs.

    This class provides aggregated statistics about all runs for a task,
    including counts of different run types and their success rates.

    Attributes:
        total_ai_runs (int): Total number of AI-navigated runs
        total_replay_runs (int): Total number of replay runs
        successful_ai_runs (int): Number of successful AI-navigated runs
        successful_replay_runs (int): Number of successful replay runs
    """

    total_ai_runs: int = Field(default=0, description="Total number of AI-navigated runs")
    total_replay_runs: int = Field(default=0, description="Total number of replay runs")
    successful_ai_runs: int = Field(default=0, description="Number of successful AI-navigated runs")
    successful_replay_runs: int = Field(default=0, description="Number of successful replay runs")


class TaskMetadata(BaseModel):
    """Enhanced task metadata with comprehensive run tracking.

    This class extends the basic task metadata to include detailed tracking
    of all AI-navigated and replay runs, along with summary statistics.

    Attributes:
        task_id (str): Unique CUID2 identifier for the task
        created_date (str): ISO timestamp when the task was created
        ai_navigated_runs (List[AINavigatedRun]): List of AI-navigated runs
        replay_runs (List[ReplayRun]): List of replay runs
        summary (TaskRunSummary): Summary statistics for all runs
    """

    task_id: str = Field(description="Unique CUID2 identifier for the task")
    created_date: str = Field(description="ISO timestamp when the task was created")
    ai_navigated_runs: List[AINavigatedRun] = Field(
        default_factory=list, description="List of AI-navigated runs"
    )
    replay_runs: List[ReplayRun] = Field(default_factory=list, description="List of replay runs")
    summary: TaskRunSummary = Field(
        default_factory=TaskRunSummary, description="Summary statistics for all runs"
    )
