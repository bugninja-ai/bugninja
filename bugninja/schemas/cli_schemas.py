from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

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
        env_path (Path): Path to the task environment file
    """

    name: str = Field(description="Human-readable task name")
    task_id: str = Field(description="Unique CUID2 identifier for the task")
    folder_name: str = Field(description="Snake case folder name")
    task_path: Path = Field(description="Path to the task directory")
    toml_path: Path = Field(description="Path to the task TOML configuration file")
    env_path: Path = Field(description="Path to the task environment file")


class TaskRunConfig(BaseModel):
    """CLI-specific configuration for task execution.

    This class handles runtime configuration settings that are specific to the CLI
    execution environment, such as browser viewport, user agent, and execution mode.
    These settings are loaded from the [run_config] section of task TOML files.
    """

    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    wait_between_actions: int = Field(
        default=1, description="Wait time between actions (in seconds)"
    )
    enable_vision: bool = Field(default=True, description="Enable vision capabilities")
    enable_memory: bool = Field(default=True, description="Enable memory capabilities")
    enable_healing: bool = Field(default=True, description="Enable healing capabilities")
    headless: bool = Field(default=False, description="Run browser in headless mode")

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
            wait_between_actions=config.get("run_config.wait_between_actions", 1),
            enable_vision=config.get("run_config.enable_vision", True),
            enable_memory=config.get("run_config.enable_memory", True),
            enable_healing=config.get("run_config.enable_healing", True),
            headless=config.get("run_config.headless", False),
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

    class Config:
        """Pydantic configuration for TaskExecutionResult model."""

        arbitrary_types_allowed = True
