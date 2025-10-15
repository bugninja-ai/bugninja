"""
Pydantic models for Bugninja API.

This module provides **type-safe, validated models** for browser automation tasks,
results, and configuration using Pydantic for comprehensive validation.

## Models

1. **BugninjaTask** - Defines browser automation tasks with validation
2. **BugninjaTaskResult** - Represents task execution outcomes
3. **BugninjaConfig** - Client configuration with environment variable support
4. **SessionInfo** - Metadata about recorded browser sessions

## Usage Examples

```python
from bugninja.api.models import BugninjaTask, BugninjaConfig

# Create a task with validation
task = BugninjaTask(
    description="Navigate to example.com and click login",
    max_steps=50,
    allowed_domains=["example.com"]
)

# Create configuration with defaults
config = BugninjaConfig(
    headless=True,
    llm_temperature=0.0
)
```
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from browser_use import BrowserProfile, BrowserSession  # type: ignore
from browser_use.browser.profile import BROWSERUSE_PROFILES_DIR  # type: ignore
from cuid2 import Cuid as CUID
from playwright._impl._api_structures import ViewportSize
from pydantic import BaseModel, Field, field_validator

from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.schemas.pipeline import Traversal
from bugninja.schemas.test_case_io import TestCaseSchema


class FileUploadInfo(BaseModel):
    """Information about a file available for upload during task execution.

    This model defines the metadata for files that can be uploaded during
    browser automation tasks, with user-friendly API and automatic indexing.

    Attributes:
        index (int): Numeric identifier for AI agent reference (auto-assigned)
        name (str): Filename with extension (e.g., "bunny.webp")
        path (Path): Filesystem path to the file (auto-converted from string)
        extension (str): File extension extracted from name (auto-populated)
        description (str): Description of file contents/purpose for AI context

    Example:
        ```python
        from bugninja.schemas.models import FileUploadInfo

        # Simple usage (recommended)
        file_info = FileUploadInfo(
            name="bunny.webp",
            path="./bunny.webp",
            description="an image about a bunny"
        )

        # Alternative factory method
        file_info = FileUploadInfo.from_user_input(
            name="resume.pdf",
            path="./resume.pdf",
            description="a resume document"
        )
        ```
    """

    # Internal fields (auto-populated)
    index: int = Field(default=0, description="Zero-based index for AI reference")
    extension: str = Field(default="", description="File extension extracted from name")

    # User-facing fields
    name: str = Field(min_length=1, description="Filename with extension")
    path: Path = Field(description="Filesystem path to the file")
    description: str = Field(description="Description of file contents/purpose")

    def __init__(self, **data) -> None:  # type: ignore
        """Initialize FileUploadInfo with automatic path conversion and extension extraction."""
        # Handle string path conversion
        if "path" in data and isinstance(data["path"], str):
            data["path"] = Path(data["path"])

        # Extract extension from name if not provided
        if "name" in data and "extension" not in data:
            name = data["name"]
            if "." in name:
                data["extension"] = Path(name).suffix
            else:
                raise ValueError(f"Filename '{name}' must include file extension")

        super().__init__(**data)

    @classmethod
    def from_user_input(
        cls, name: str, path: Union[str, Path], description: str, index: Optional[int] = None
    ) -> "FileUploadInfo":
        """Create FileUploadInfo from user-friendly inputs.

        Args:
            name (str): Filename with extension (e.g., "bunny.webp")
            path (Union[str, Path]): File path as string or Path object
            description (str): Description of the file
            index (Optional[int]): Optional index (auto-assigned if not provided)

        Returns:
            FileUploadInfo: Configured file upload info
        """
        return cls(name=name, path=path, description=description, index=index or 0)

    @field_validator("name")
    @classmethod
    def validate_name_has_extension(cls, v: str) -> str:
        """Validate filename contains extension."""
        if "." not in v:
            raise ValueError(f"Filename '{v}' must include file extension")
        return v

    @field_validator("path")
    @classmethod
    def validate_path_exists(cls, v: Union[str, Path]) -> Path:
        """Convert string to Path and validate existence.

        Args:
            v (Union[str, Path]): The file path to validate

        Returns:
            Path: The validated file path

        Raises:
            ValueError: If file doesn't exist or is not a file
        """
        # Convert string to Path if needed
        if isinstance(v, str):
            v = Path(v)

        if not v.exists():
            raise ValueError(f"File not found at path: {v}")
        if not v.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v


class OperationType(Enum):
    """Enumeration of operation types for Bugninja operations."""

    FIRST_TRAVERSAL = "first_traversal"  # Navigation agent creating new traversal
    REPLAY = "replay"  # Replicator replaying existing traversal


class HealingStatus(Enum):
    """Enumeration of healing status for Bugninja operations."""

    NONE = "none"  # No healing occurred
    USED = "used"  # Healing was used and successful
    FAILED = "failed"  # Healing was attempted but failed


class BugninjaErrorType(Enum):
    """Classification of different error types for proper result handling."""

    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    LLM_ERROR = "llm_error"
    BROWSER_ERROR = "browser_error"
    TASK_EXECUTION_ERROR = "task_execution_error"
    SESSION_REPLAY_ERROR = "session_replay_error"
    CLEANUP_ERROR = "cleanup_error"
    UNKNOWN_ERROR = "unknown_error"


class BugninjaTask(BaseModel):
    """Represents a browser automation task with comprehensive validation.

    This model defines a task to be executed by the Bugninja automation engine.
    It supports both **config file-based tasks** and **direct parameter tasks** for
    maximum flexibility. It includes validation for all fields and provides comprehensive
    documentation for task configuration and execution parameters.

    Attributes:
        task_config_path (Optional[Path]): Path to task_{name}.toml configuration file
        description (str): Human-readable description of the task to perform (1-1000 chars)
        start_url (Optional[str]): URL where the browser session should start before executing the task
        extra_instructions (List[str]): List of extra instructions for navigation
        max_steps (int): Maximum number of steps to execute (1-1000, default: 100)
        enable_healing (bool): Enable self-healing capabilities for replay tasks (default: True)
        custom_config (Optional[Dict[str, Any]]): Custom configuration overrides
        allowed_domains (Optional[List[str]]): List of allowed domains for navigation
        secrets (Optional[Dict[str, Any]]): Sensitive data for authentication

    Example:
        ```python
        from bugninja.api.models import BugninjaTask
        from pathlib import Path

        # Task from config file (NEW)
        task = BugninjaTask(task_config_path=Path("tasks/login_flow/task_login_flow.toml"))

        # Direct task (backward compatibility)
        task = BugninjaTask(
            description="Navigate to example.com and click login",
            start_url="https://example.com"
        )

        # Advanced task with all options
        task = BugninjaTask(
            description="Complete user registration flow",
            start_url="https://example.com/register",
            extra_instructions=["Take screenshot after each step"],
            max_steps=75,
            enable_healing=True,
            allowed_domains=["example.com", "api.example.com"],
            secrets={
                "username": "test@example.com",
                "password": "secure_password"
            }
        )
        ```
    """

    start_url: Optional[str] = Field(
        default=None,
        description="URL where the browser session should start before executing the task",
    )

    # Config file support
    task_config_path: Optional[Path] = Field(
        default=None, description="Path to task_{name}.toml configuration file"
    )

    # Task description and instructions
    description: str = Field(
        default="",
        min_length=0,
        max_length=10000,
        description="Human-readable description of the task to perform",
    )

    extra_instructions: List[str] = Field(
        default_factory=list, description="List of extra instruction for navigation"
    )

    # Task execution settings
    run_id: str = Field(
        default_factory=lambda: CUID().generate(), description="Unique identifier for the task run"
    )

    max_steps: int = Field(
        default=100, ge=1, le=200, description="Maximum number of steps to execute"
    )

    enable_healing: bool = Field(
        default=True,
        description="Enable self-healing capabilities. Only holds meaning for replay tasks",
    )

    # Legacy fields (for backward compatibility)
    custom_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom configuration overrides"
    )

    allowed_domains: Optional[List[str]] = Field(
        default=None, description="List of allowed domains for navigation"
    )

    secrets: Optional[Dict[str, Any]] = Field(
        default=None, description="Sensitive data for authentication and task execution"
    )

    # Task dependency configuration (static, not run-specific)
    # Each entry may be a task folder name or a CUID; resolution prefers folder name, then CUID.
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task identifiers (folder or CUID) this task depends on",
    )

    # I/O Schema support
    io_schema: Optional["TestCaseSchema"] = Field(
        default=None, description="Unified input and output schema for this test case"
    )

    # File upload support
    available_files: Optional[List["FileUploadInfo"]] = Field(
        default=None, description="Files available for upload during task execution"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate task description is not empty or whitespace-only.

        Args:
            v (str): The description value to validate

        Returns:
            str: The validated and stripped description

        Raises:
            ValueError: If description is empty or whitespace-only
        """
        if v and not v.strip():
            raise ValueError("BugninjaTask description cannot be empty or whitespace-only")
        return v.strip() if v else ""

    @field_validator("available_files")
    @classmethod
    def auto_assign_file_indices(
        cls, v: Optional[List[FileUploadInfo]]
    ) -> Optional[List[FileUploadInfo]]:
        """Auto-assign indices to files and validate uniqueness.

        Args:
            v (Optional[List[FileUploadInfo]]): List of file upload info objects

        Returns:
            Optional[List[FileUploadInfo]]: List with auto-assigned indices

        Raises:
            ValueError: If duplicate filenames are found
        """
        if not v:
            return v

        # Auto-assign indices based on list position
        for idx, file_info in enumerate(v):
            file_info.index = idx

        # Validate no duplicate names
        names = [f.name for f in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate filenames not allowed in available_files")

        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to load configuration from file if provided."""
        if self.task_config_path:
            self._load_from_config_file()

    def _load_from_config_file(self) -> None:
        """Load task configuration from TOML file.

        This method loads task-specific configuration from the provided TOML file,
        including task description, agent settings, and secrets from the TOML file.

        Raises:
            FileNotFoundError: If task config file doesn't exist
            ValueError: If TOML file is malformed or invalid
        """

        if not self.task_config_path or not self.task_config_path.exists():
            raise FileNotFoundError(f"Task config file not found: {self.task_config_path}")

        from bugninja.config.factory import ConfigurationFactory

        try:
            # Load task configuration from TOML (includes secrets)
            task_config = ConfigurationFactory.load_task_config(self.task_config_path)

            # Update task properties from config
            self._update_from_config(task_config)

        except Exception as e:
            raise ValueError(f"Configuration error: {str(e)}")

    def _update_from_config(
        self,
        task_config: Dict[str, Any],
    ) -> None:
        """Update task properties from configuration data.

        Args:
            task_config: Task-specific configuration from TOML (flattened)
        """
        # Update task description and instructions (config is flattened)
        self.description = task_config.get("task.description", "")
        self.start_url = task_config.get("task.start_url", None)
        self.extra_instructions = task_config.get("task.extra_instructions", [])

        # Update secrets from TOML config
        if "task_secrets" in task_config:
            self.secrets = task_config["task_secrets"]

        # Update allowed domains if present
        if "task.allowed_domains" in task_config:
            allowed_domains: Optional[List[str]] = task_config.get("task.allowed_domains")
            if allowed_domains and len(allowed_domains):
                self.allowed_domains = allowed_domains

        # Update dependencies if present
        if "task.dependencies" in task_config:
            deps = task_config.get("task.dependencies")
            # Accept only list[str]; ignore invalid forms silently to avoid breaking existing tasks
            if isinstance(deps, list):
                # keep only string-like identifiers
                self.dependencies = [str(d) for d in deps]

        # Update I/O schemas if present
        io_schema_data = task_config.get("task.io_schema", {})
        input_schema_data = io_schema_data.get("input_schema")
        output_schema_data = io_schema_data.get("output_schema")

        if input_schema_data or output_schema_data:
            self.io_schema = TestCaseSchema(
                input_schema=input_schema_data, output_schema=output_schema_data
            )

        # Update available files if present
        files_data = task_config.get("task.files", [])
        if files_data:
            available_files: List[FileUploadInfo] = []
            for idx, file_config in enumerate(files_data):
                # Resolve file path relative to task directory in CLI mode
                file_path = Path(file_config["path"])
                if not file_path.is_absolute() and self.task_config_path:
                    # In CLI mode, resolve relative to task directory (not files subdirectory)
                    task_dir = self.task_config_path.parent
                    file_path = task_dir / file_path

                # Extract extension from name or path if not provided
                extension = file_config.get("extension", "")
                if not extension:
                    name = file_config.get("name", file_path.name)
                    extension = Path(name).suffix

                available_files.append(
                    FileUploadInfo(
                        index=idx,  # Auto-assigned
                        name=file_config.get("name", file_path.name),
                        path=file_path,
                        extension=extension,
                        description=file_config["description"],
                    )
                )

            self.available_files = available_files

    class Config:
        """Pydantic configuration for BugninjaTask model."""

        json_schema_extra = {
            "example": {
                "description": "Navigate to example.com and click the login button",
                "start_url": "https://example.com",
                "max_steps": 50,
                "enable_healing": True,
                "allowed_domains": ["example.com"],
                "secrets": {"username": "user@example.com", "password": "secret"},
            }
        }


class BugninjaTaskResult(BaseModel):
    """Result of any Bugninja operation (navigation or replay).

    This model represents the **outcome of any Bugninja operation**, including
    success status, operation type, healing status, and execution metadata.
    It provides comprehensive information about the operation's execution
    and results for analysis and debugging.

    Attributes:
        success (bool): Whether the operation completed successfully
        operation_type (OperationType): Type of operation (first_traversal or replay)
        healing_status (HealingStatus): Whether healing was used during the operation
        execution_time (float): Execution time in seconds (>= 0.0)
        steps_completed (int): Number of steps completed (>= 0)
        total_steps (int): Total number of steps in the operation (>= 0)
        traversal (Optional[Traversal]): The actual Traversal object (if successful)
        error (Optional[BugninjaTaskError]): Error object if operation failed
        traversal_file (Optional[Path]): Path to the traversal JSON file
        screenshots_dir (Optional[Path]): Directory containing screenshots
        created_at (datetime): Timestamp when the result was created
        metadata (Dict[str, Any]): Additional execution metadata

    Example:
        ```python
        from bugninja.api.models import BugninjaTaskResult, OperationType, HealingStatus

        # Successful result
        result = BugninjaTaskResult(
            success=True,
            operation_type=OperationType.FIRST_TRAVERSAL,
            healing_status=HealingStatus.NONE,
            execution_time=45.2,
            steps_completed=15,
            total_steps=20,
            traversal_file=Path("./traversals/session.json"),
            metadata={"screenshots_taken": 5}
        )

        # Failed result with error
        result = BugninjaTaskResult(
            success=False,
            operation_type=OperationType.REPLAY,
            healing_status=HealingStatus.FAILED,
            execution_time=12.5,
            steps_completed=3,
            total_steps=20,
            error=BugninjaTaskError(
                error_type=BugninjaErrorType.BROWSER_ERROR,
                message="Element not found",
                suggested_action="Check if element still exists on page"
            )
        )
        ```
    """

    success: bool = Field(description="Whether the operation completed successfully")

    operation_type: OperationType = Field(description="Type of operation performed")

    healing_status: HealingStatus = Field(
        default=HealingStatus.NONE, description="Whether healing was used during the operation"
    )

    execution_time: float = Field(ge=0.0, description="Execution time in seconds")

    steps_completed: int = Field(ge=0, description="Number of steps completed")

    total_steps: int = Field(ge=0, description="Total number of steps in the operation")

    traversal: Optional[Traversal] = Field(default=None, description="The actual Traversal object")

    error: Optional["BugninjaTaskError"] = Field(
        default=None, description="Error object if operation failed"
    )

    traversal_file: Optional[Path] = Field(
        default=None, description="Path to the traversal JSON file"
    )

    screenshots_dir: Optional[Path] = Field(
        default=None, description="Directory containing screenshots"
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when the result was created"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )

    class Config:
        """Pydantic configuration for BugninjaTaskResult model."""

        json_schema_extra = {
            "example": {
                "success": True,
                "operation_type": "first_traversal",
                "healing_status": "none",
                "execution_time": 45.2,
                "steps_completed": 15,
                "total_steps": 20,
                "traversal_file": "/path/to/traversal.json",
                "screenshots_dir": "/path/to/screenshots/",
                "metadata": {"screenshots_taken": 5},
            }
        }


class BugninjaTaskError(BaseModel):
    """Enhanced error model for task results with classification and suggestions.

    This model provides **comprehensive error information** including error type
    classification, detailed error messages, and suggested actions for resolution.

    Attributes:
        error_type (BugninjaErrorType): Classification of the error type
        message (str): Human-readable error message
        details (Optional[Dict[str, Any]]): Additional error details for debugging
        original_error (Optional[str]): Original exception information
        suggested_action (Optional[str]): Suggested action to resolve the error

    Example:
        ```python
        from bugninja.api.models import BugninjaTaskError, BugninjaErrorType

        error = BugninjaTaskError(
            error_type=BugninjaErrorType.BROWSER_ERROR,
            message="Element 'login-button' not found on page",
            details={"page_url": "https://example.com", "selector": "#login-button"},
            original_error="ElementNotFoundError: Element not found",
            suggested_action="Check if the login button still exists and has the correct selector"
        )
        ```
    """

    error_type: BugninjaErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    original_error: Optional[str] = None
    suggested_action: Optional[str] = None

    def __str__(self) -> str:
        """Return a human-readable error message with proper formatting.

        Returns:
            str: Formatted error message with details and suggestions
        """
        import json

        # Start with the main error message
        error_parts = [f"🚨 {self.message}"]

        # Add error type if available
        if self.error_type:
            error_parts.append(f"📋 Error Type: {self.error_type.value}")

        # Add details if available (formatted nicely)
        if self.details:
            error_parts.append("📝 Details:")
            try:
                # Format details as pretty JSON
                formatted_details = json.dumps(self.details, indent=2, default=str)
                # Indent each line of details
                indented_details = "\n".join(f"  {line}" for line in formatted_details.split("\n"))
                error_parts.append(indented_details)
            except Exception:
                # Fallback to string representation
                error_parts.append(f"  {self.details}")

        # Add original error if available
        if self.original_error:
            error_parts.append(f"🔍 Original Error: {self.original_error}")

        # Add suggested action if available
        if self.suggested_action:
            error_parts.append(f"💡 Suggested Action: {self.suggested_action}")

        return "\n".join(error_parts)


class BulkBugninjaTaskResult(BaseModel):
    """Result for parallel task execution with aggregate metrics.

    This model represents the **aggregate result** of executing multiple tasks
    in parallel, providing comprehensive metrics and individual task results
    for analysis and monitoring.

    Attributes:
        overall_success (bool): Whether all tasks completed successfully
        total_tasks (int): Total number of tasks executed
        successful_tasks (int): Number of tasks that completed successfully
        failed_tasks (int): Number of tasks that failed
        total_execution_time (float): Total time spent executing all tasks
        individual_results (List[BugninjaTaskResult]): Results for each individual task
        metadata (Dict[str, Any]): Additional metadata about the bulk operation
        error_summary (Optional[Dict[BugninjaErrorType, int]]): Summary of error types and counts

    Example:
        ```python
        from bugninja.api.models import BulkBugninjaTaskResult

        bulk_result = BulkBugninjaTaskResult(
            overall_success=False,
            total_tasks=5,
            successful_tasks=3,
            failed_tasks=2,
            total_execution_time=120.5,
            individual_results=[task_result_1, task_result_2, ...],
            error_summary={
                BugninjaErrorType.BROWSER_ERROR: 1,
                BugninjaErrorType.LLM_ERROR: 1
            },
            metadata={"operation": "parallel_execution"}
        )
        ```
    """

    overall_success: bool
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_execution_time: float
    individual_results: List[BugninjaTaskResult]
    metadata: Dict[str, Any]
    error_summary: Optional[Dict[BugninjaErrorType, int]] = None


class BugninjaConfig(BaseModel):
    """Configuration for Bugninja client with comprehensive validation.

    This model provides **comprehensive configuration options** for the Bugninja
    automation engine with validation and direct configuration support. It includes
    settings for LLM, browser, task execution, and development environments.

    Attributes:
        llm_provider (str): LLM provider to use (default: "azure_openai")
        llm_temperature (float): Temperature for LLM responses (0.0-2.0, default: 0.0)
        headless (bool): Run browser in headless mode (default: False)
        viewport_width (int): Browser viewport width (800-3840, default: 1920)
        viewport_height (int): Browser viewport height (600-2160, default: 1080)
        user_agent (Optional[str]): Browser user agent string
        strict_selectors (bool): Use strict selectors for element identification (default: True)
        user_data_dir (Optional[Union[Path, str]]): Directory for browser user data
        default_max_steps (int): Default maximum steps for tasks (1-1000, default: 100)
        enable_screenshots (bool): Enable screenshot capture (default: True)
        enable_healing (bool): Enable self-healing capabilities (default: True)
        debug_mode (bool): Enable debug mode (default: False)
        screenshots_dir (Path): Directory for storing screenshots (default: "./screenshots")
        traversals_dir (Path): Directory for storing traversal files (default: "./traversals")
        video_recording (Optional[VideoRecordingConfig]): Video recording configuration (default: None)

    Example:
        ```python
        from bugninja.api.models import BugninjaConfig

        # Basic configuration with defaults
        config = BugninjaConfig()

        # Advanced configuration
        config = BugninjaConfig(
            llm_temperature=0.0,
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            enable_healing=True,
            debug_mode=True,
            screenshots_dir=Path("./custom_screenshots"),
            traversals_dir=Path("./custom_traversals")
        )
        ```
    """

    # LLM Configuration
    llm_provider: str = Field(
        default="azure_openai",
        description="LLM provider to use",
    )

    llm_temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Temperature for LLM responses"
    )

    # Provider-specific LLM configuration
    llm_config: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific LLM configuration parameters"
    )

    # Browser Configuration
    headless: bool = Field(default=False, description="Run browser in headless mode")

    viewport_width: int = Field(default=1920, description="Browser viewport width")

    viewport_height: int = Field(default=1080, description="Browser viewport height")

    user_agent: Optional[str] = Field(
        default=None,
        description="Browser user agent string",
    )

    strict_selectors: bool = Field(
        default=True, description="Use strict selectors for element identification"
    )

    user_data_dir: Optional[Union[Path, str]] = Field(
        default=BROWSERUSE_PROFILES_DIR / "default",
        description="Directory for browser user data (cookies, cache, etc.)",
    )

    # BugninjaTask Configuration
    default_max_steps: int = Field(
        default=100, ge=1, le=200, description="Default maximum steps for tasks"
    )

    enable_screenshots: bool = Field(default=True, description="Enable screenshot capture")

    enable_healing: bool = Field(default=True, description="Enable self-healing capabilities")

    # Development Configuration
    debug_mode: bool = Field(default=False, description="Enable debug mode")

    # File Paths
    output_base_dir: Optional[Path] = Field(
        default=None,
        description="Base directory for all output files (traversals, screenshots, videos)",
    )

    screenshots_dir: Optional[Path] = Field(
        default=Path("./screenshots"), description="Directory for storing screenshots"
    )

    traversals_dir: Path = Field(
        default=Path("./traversals"), description="Directory for storing traversal files"
    )

    # Video Recording Configuration
    video_recording: Optional[VideoRecordingConfig] = Field(
        default=None,
        description="Video recording configuration for navigation sessions",
    )

    # Internal flag to indicate CLI usage (excluded from serialization)
    cli_mode: bool = Field(
        default=False,
        exclude=True,
        description="Internal flag indicating if this config is used by CLI (prevents automatic directory creation)",
    )

    @field_validator("screenshots_dir", "traversals_dir", "user_data_dir")
    @classmethod
    def validate_paths(cls, v: Path) -> Path:
        """Validate path fields without creating directories.

        Args:
            v (Path): The path to validate

        Returns:
            Path: The validated path (directories are not created automatically)
        """
        # Just validate the path, don't create directories
        # Directory creation is now handled explicitly when needed
        return v

    def get_effective_screenshots_dir(self) -> Optional[Path]:
        """Get the effective screenshots directory based on output_base_dir.

        Returns:
            Path: The screenshots directory to use
        """
        if self.output_base_dir:
            return self.output_base_dir / "screenshots"
        return self.screenshots_dir

    def get_effective_traversals_dir(self) -> Path:
        """Get the effective traversals directory based on output_base_dir.

        Returns:
            Path: The traversals directory to use
        """
        if self.output_base_dir:
            return self.output_base_dir / "traversals"
        return self.traversals_dir

    def get_effective_video_dir(self) -> Path:
        """Get the effective video directory based on output_base_dir.

        Returns:
            Path: The video directory to use
        """
        if self.output_base_dir:
            return self.output_base_dir / "videos"
        return Path(self.video_recording.output_dir) if self.video_recording else Path("./videos")

    def ensure_directories_exist(self) -> None:
        """Explicitly create directories when needed.

        This method creates the necessary directories for screenshots, traversals,
        and user data. It should be called before starting any browser automation
        operations that will use these directories.

        Note:
            This method is called automatically by BugninjaClient before task execution
            and session replay. CLI usage does not require this as it manages its own
            directory structure.
        """
        # Skip directory creation if in CLI mode
        if self.cli_mode:
            return
        directories_to_create: List[Path] = []

        # Add screenshots directory
        if self.screenshots_dir is not None:
            # Use effective screenshots directory for CLI mode
            effective_screenshots_dir = self.get_effective_screenshots_dir()
            if effective_screenshots_dir:
                directories_to_create.append(effective_screenshots_dir)

        # Add traversals directory
        if self.traversals_dir is not None:
            # Use effective traversals directory for CLI mode
            effective_traversals_dir = self.get_effective_traversals_dir()
            directories_to_create.append(effective_traversals_dir)

        # Add user data directory
        if self.user_data_dir is not None:
            directories_to_create.append(
                self.user_data_dir
                if isinstance(self.user_data_dir, Path)
                else Path(self.user_data_dir)
            )

        # Create all directories
        for directory in directories_to_create:
            if directory is not None:
                directory.mkdir(parents=True, exist_ok=True)

    class Config:
        """Pydantic configuration for BugninjaConfig model."""

        json_schema_extra = {
            "example": {
                "llm_provider": "azure_openai",
                "headless": False,
                "viewport_width": 1280,
                "viewport_height": 960,
                "enable_healing": True,
                "strict_selectors": True,
            }
        }

    def build_bugninja_session_from_config_for_run(self, run_id: str) -> BrowserSession:
        """Build a browser session from configuration with run isolation.

        This method creates a `BrowserSession` instance configured with the current
        configuration settings and isolated browser data directory for the specific run.

        Args:
            run_id (str): Unique identifier for the run to create isolated browser data

        Returns:
            BrowserSession: Configured browser session with isolated data directory

        Example:
            ```python
            config = BugninjaConfig()
            session = config.build_bugninja_session_from_config_for_run("run_123")
            # Session is now configured with isolated browser data in ./data_dir/run_run_123/
            ```
        """

        # Override user_data_dir with run_id for browser isolation
        base_dir = self.user_data_dir or Path("./data_dir")
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        isolated_dir = base_dir / f"run_{run_id}"

        viewport_size = ViewportSize(width=self.viewport_width, height=self.viewport_height)

        return BrowserSession(
            browser_profile=BrowserProfile(
                headless=self.headless,
                viewport=viewport_size,
                window_size=viewport_size,
                user_agent=self.user_agent,
                strict_selectors=self.strict_selectors,
                user_data_dir=isolated_dir,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                # record_video_dir="./recordings",
                # record_video_size=viewport,
            )
        )


class SessionInfo(BaseModel):
    """Information about a recorded browser session.

    This model provides **metadata about a recorded session** including
    file path, creation time, and session statistics for session management
    and replay operations.

    Attributes:
        file_path (Path): Path to the session file
        created_at (datetime): When the session was created
        steps_count (int): Number of steps in the session (>= 0)
        success (bool): Whether the session completed successfully
        metadata (Dict[str, Any]): Additional session metadata

    Example:
        ```python
        from bugninja.api.models import SessionInfo
        from pathlib import Path
        from datetime import datetime

        session_info = SessionInfo(
            file_path=Path("./traversals/session_20240115.json"),
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            steps_count=25,
            success=True,
            metadata={"browser_version": "120.0.0", "task_type": "login_flow"}
        )
        ```
    """

    file_path: Path = Field(description="Path to the session file")

    created_at: datetime = Field(description="When the session was created")

    steps_count: int = Field(ge=0, description="Number of steps in the session")

    success: bool = Field(description="Whether the session completed successfully")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    class Config:
        """Pydantic configuration for SessionInfo model."""

        json_schema_extra = {
            "example": {
                "file_path": "/path/to/session.json",
                "created_at": "2024-01-15T10:30:00",
                "steps_count": 25,
                "success": True,
            }
        }
