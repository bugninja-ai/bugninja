"""
Pydantic models for Bugninja API.

This module provides type-safe, validated models for browser automation tasks,
results, and configuration using Pydantic for comprehensive validation.

## Models

1. **BugninjaTask** - Defines browser automation tasks with validation
2. **BugninjaTaskResult** - Represents task execution outcomes
3. **BugninjaConfig** - Client configuration with environment variable support
4. **SessionInfo** - Metadata about recorded browser sessions
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from browser_use.browser.profile import BROWSERUSE_PROFILES_DIR  # type: ignore
from pydantic import BaseModel, Field, field_validator

from bugninja.schemas.pipeline import Traversal


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


# TODO!:AGENT we have to have a better name for Tasks, like BugninjaTask
class BugninjaTask(BaseModel):
    """Represents a browser automation task.

    This model defines a task to be executed by the Bugninja automation engine.
    It includes validation for all fields and provides comprehensive documentation.

    ## Fields

    1. **description** - Human-readable task description (required)
    3. **max_steps** - Maximum number of steps to execute (1-1000)
    4. **enable_healing** - Enable self-healing capabilities
    5. **custom_config** - Custom configuration overrides
    6. **allowed_domains** - List of allowed domains for navigation
    7. **secrets** - Sensitive data for authentication
    """

    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable description of the task to perform",
    )

    max_steps: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of steps to execute"
    )

    enable_healing: bool = Field(
        default=True,
        description="Enable self-healing capabilities. Only holds meaning for replay tasks",
    )

    custom_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom configuration overrides"
    )

    allowed_domains: Optional[List[str]] = Field(
        default=None, description="List of allowed domains for navigation"
    )

    secrets: Optional[Dict[str, Any]] = Field(
        default=None, description="Sensitive data for authentication and task execution"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate task description is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("BugninjaTask description cannot be empty or whitespace-only")
        return v.strip()

    class Config:
        """Pydantic configuration for BugninjaTask model."""

        json_schema_extra = {
            "example": {
                "description": "Navigate to example.com and click the login button",
                "max_steps": 50,
                "enable_healing": True,
                "allowed_domains": ["example.com"],
                "secrets": {"username": "user@example.com", "password": "secret"},
            }
        }


class BugninjaTaskResult(BaseModel):
    """Result of any Bugninja operation (navigation or replay).

    This model represents the outcome of any Bugninja operation, including
    success status, operation type, healing status, and execution metadata.

    ## Fields

    1. **success** - Whether the operation completed successfully
    2. **operation_type** - Type of operation (first_traversal or replay)
    3. **healing_status** - Whether healing was used during the operation
    4. **execution_time** - Execution time in seconds
    5. **steps_completed** - Number of steps completed
    6. **total_steps** - Total number of steps in the operation
    7. **traversal** - The actual Traversal object (if successful)
    8. **error** - Error object if operation failed
    9. **traversal_file** - Path to the traversal JSON file
    10. **screenshots_dir** - Directory containing screenshots
    11. **created_at** - Timestamp when the result was created
    12. **metadata** - Additional execution metadata
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
    """Enhanced error model for task results."""

    error_type: BugninjaErrorType
    message: str
    details: Optional[Dict[str, Any]] = None
    original_error: Optional[str] = None
    suggested_action: Optional[str] = None


class BulkBugninjaTaskResult(BaseModel):
    """Result for parallel task execution."""

    overall_success: bool
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_execution_time: float
    individual_results: List[BugninjaTaskResult]
    metadata: Dict[str, Any]
    error_summary: Optional[Dict[BugninjaErrorType, int]] = None


# Backward compatibility alias
BugninjaTaskResult = BugninjaTaskResult


class BugninjaConfig(BaseModel):
    """Configuration for Bugninja client.

    This model provides comprehensive configuration options for the Bugninja
    automation engine with validation and direct configuration support.

    ## Configuration Sections

    1. **LLM Configuration** - Language model settings
    2. **Browser Configuration** - Browser automation settings
    3. **BugninjaTask Configuration** - Default task parameters
    4. **Development Configuration** - Debug and logging settings
    5. **File Paths** - Directory configurations
    """

    # LLM Configuration
    llm_provider: str = Field(
        default="azure_openai",
        description="LLM provider to use",
    )

    llm_model: str = Field(default="gpt-4.1", description="LLM model to use")

    llm_temperature: float = Field(
        default=0.001, ge=0.0, le=2.0, description="Temperature for LLM responses"
    )

    # Browser Configuration
    headless: bool = Field(default=False, description="Run browser in headless mode")

    viewport_width: int = Field(default=1280, ge=800, le=3840, description="Browser viewport width")

    viewport_height: int = Field(
        default=960, ge=600, le=2160, description="Browser viewport height"
    )

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
        default=100, ge=1, le=1000, description="Default maximum steps for tasks"
    )

    enable_screenshots: bool = Field(default=True, description="Enable screenshot capture")

    enable_healing: bool = Field(default=True, description="Enable self-healing capabilities")

    # Development Configuration
    debug_mode: bool = Field(default=False, description="Enable debug mode")

    verbose_logging: bool = Field(default=False, description="Enable verbose logging")

    # File Paths
    screenshots_dir: Path = Field(
        default=Path("./screenshots"), description="Directory for storing screenshots"
    )

    traversals_dir: Path = Field(
        default=Path("./traversals"), description="Directory for storing traversal files"
    )

    @field_validator("screenshots_dir", "traversals_dir", "user_data_dir")
    @classmethod
    def create_directories_if_not_exist(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        if v is not None:
            v.mkdir(parents=True, exist_ok=True)
        return v

    class Config:
        """Pydantic configuration for BugninjaConfig model."""

        json_schema_extra = {
            "example": {
                "llm_provider": "azure_openai",
                "llm_model": "gpt-4.1",
                "headless": False,
                "viewport_width": 1280,
                "viewport_height": 960,
                "enable_healing": True,
                "strict_selectors": True,
            }
        }


class SessionInfo(BaseModel):
    """Information about a recorded browser session.

    This model provides metadata about a recorded session including
    file path, creation time, and session statistics.

    ## Fields

    1. **file_path** - Path to the session file
    2. **created_at** - When the session was created
    3. **steps_count** - Number of steps in the session
    5. **success** - Whether the session completed successfully
    6. **metadata** - Additional session metadata
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
