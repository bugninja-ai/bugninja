"""
Pydantic models for Bugninja API.

This module provides type-safe, validated models for browser automation tasks,
results, and configuration using Pydantic for comprehensive validation.

## Models

1. **Task** - Defines browser automation tasks with validation
2. **TaskResult** - Represents task execution outcomes
3. **BugninjaConfig** - Client configuration with environment variable support
4. **SessionInfo** - Metadata about recorded browser sessions
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
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
    8. **extend_planner_system_message** - Custom system message for the planner
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

    enable_healing: bool = Field(default=True, description="Enable self-healing capabilities")

    custom_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom configuration overrides"
    )

    allowed_domains: Optional[List[str]] = Field(
        default=None, description="List of allowed domains for navigation"
    )

    secrets: Optional[Dict[str, Any]] = Field(
        default=None, description="Sensitive data for authentication and task execution"
    )

    extend_planner_system_message: Optional[str] = Field(
        default=None, description="Custom system message to extend the planner's capabilities"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate task description is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Task description cannot be empty or whitespace-only")
        return v.strip()

    class Config:
        """Pydantic configuration for Task model."""

        json_schema_extra = {
            "example": {
                "description": "Navigate to example.com and click the login button",
                "max_steps": 50,
                "enable_healing": True,
                "allowed_domains": ["example.com"],
                "secrets": {"username": "user@example.com", "password": "secret"},
            }
        }


class TaskResult(BaseModel):
    """Result of a browser automation task.

    This model represents the outcome of a task execution, including
    success status, session file location, and execution metadata.

    ## Fields

    1. **success** - Whether the task completed successfully
    2. **session_file** - Path to the recorded session file
    3. **error_message** - Error message if task failed
    4. **steps_completed** - Number of steps completed
    5. **execution_time** - Execution time in seconds
    6. **metadata** - Additional execution metadata
    7. **created_at** - Timestamp when the result was created
    8. **traversal_file** - Path to the traversal JSON file
    9. **screenshots_dir** - Directory containing screenshots for this task
    """

    success: bool = Field(description="Whether the task completed successfully")

    session_file: Optional[Path] = Field(None, description="Path to the recorded session file")

    error_message: Optional[str] = Field(None, description="Error message if task failed")

    steps_completed: int = Field(default=0, ge=0, description="Number of steps completed")

    execution_time: Optional[float] = Field(None, ge=0.0, description="Execution time in seconds")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when the result was created"
    )

    traversal_file: Optional[Path] = Field(None, description="Path to the traversal JSON file")

    screenshots_dir: Optional[Path] = Field(
        None, description="Directory containing screenshots for this task"
    )

    class Config:
        """Pydantic configuration for TaskResult model."""

        json_schema_extra = {
            "example": {
                "success": True,
                "session_file": "/path/to/session.json",
                "traversal_file": "/path/to/traversal.json",
                "screenshots_dir": "/path/to/screenshots/",
                "steps_completed": 15,
                "execution_time": 45.2,
                "metadata": {"screenshots_taken": 5},
            }
        }


class BugninjaConfig(BaseModel):
    """Configuration for Bugninja client.

    This model provides comprehensive configuration options for the Bugninja
    automation engine with validation and environment variable support.

    ## Configuration Sections

    1. **LLM Configuration** - Language model settings
    2. **Browser Configuration** - Browser automation settings
    3. **Task Configuration** - Default task parameters
    4. **Development Configuration** - Debug and logging settings
    5. **File Paths** - Directory configurations
    """

    # LLM Configuration
    llm_provider: str = Field(
        default="azure_openai",
        pattern="^(azure_openai|openai|anthropic)$",
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

    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="Browser user agent string",
    )

    strict_selectors: bool = Field(
        default=True, description="Use strict selectors for element identification"
    )

    # Task Configuration
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

    logs_dir: Path = Field(default=Path("./logs"), description="Directory for storing log files")

    @field_validator("screenshots_dir", "traversals_dir", "logs_dir")
    @classmethod
    def create_directories_if_not_exist(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    class Config:
        """Pydantic configuration for BugninjaConfig model."""

        env_prefix = "BUGNINJA_"
        case_sensitive = False
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
