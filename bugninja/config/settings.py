"""
Core configuration settings for Bugninja using Pydantic Settings.

This module provides type-safe configuration management with TOML file support
for project settings and environment variables for sensitive data, validation,
and default values for all Bugninja components.
"""

from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from bugninja.events.types import EventPublisherType


class BugninjaSettings(BaseSettings):
    """Main configuration settings for Bugninja framework.

    This class provides centralized configuration management with:
    - Type-safe configuration with validation
    - TOML file support for project settings
    - Environment variable support for sensitive data (API keys, passwords)
    - Code-based defaults for missing values
    - Nested configuration support
    """

    # LLM Configuration (Sensitive - from .env)
    azure_openai_endpoint: str = Field(
        ..., alias="AZURE_OPENAI_ENDPOINT", description="Azure OpenAI endpoint URL"
    )
    azure_openai_key: SecretStr = Field(
        ..., alias="AZURE_OPENAI_KEY", description="Azure OpenAI API key"
    )

    # LLM Configuration (Non-sensitive - from TOML)
    azure_openai_model: str = Field(default="gpt-4.1", description="Azure OpenAI model name")
    azure_openai_temperature: float = Field(
        default=0.001,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version",
    )

    # Event Publisher Configuration (from TOML)
    event_publishers: List[EventPublisherType] = Field(
        default=[EventPublisherType.NULL], description="List of event publisher types to use"
    )

    # Logging Configuration (from TOML)
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string",
    )
    enable_rich_logging: bool = Field(default=True, description="Enable rich console logging")

    # Development Configuration (from TOML)
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    enable_verbose_logging: bool = Field(
        default=False,
        description="Enable verbose logging for debugging",
    )

    # Project Configuration (from TOML)
    project_name: str = Field(
        default="bugninja",
        description="Project name for identification and logging",
    )

    # File Paths Configuration (from TOML)
    traversals_dir: Path = Field(
        default=Path("./traversals"),
        description="Directory for storing traversal files",
    )

    # Code-based Browser Configuration (not from environment)
    @property
    def browser_config(self) -> Dict[str, Any]:
        """Get browser configuration with code-based defaults."""
        return {
            "viewport_width": 1280,
            "viewport_height": 960,
            "user_agent": None,
            "device_scale_factor": None,
            "timeout": 30_000,
        }

    # Code-based Agent Configuration (not from environment)
    @property
    def agent_config(self) -> Dict[str, Any]:
        """Get agent configuration with code-based defaults."""
        return {
            "max_steps": 100,
            "planner_interval": 5,
            "enable_vision": True,
            "enable_memory": False,
            "wait_between_actions": 0.1,
        }

    # Code-based Replicator Configuration (not from environment)
    @property
    def replicator_config(self) -> Dict[str, Any]:
        """Get replicator configuration with code-based defaults."""
        return {
            "sleep_after_actions": 1.0,
            "pause_after_each_step": True,
            "fail_on_unimplemented_action": False,
            "max_retries": 2,
            "retry_delay": 0.5,
        }

    # Code-based Screenshot Configuration (not from environment)
    @property
    def screenshot_config(self) -> Dict[str, Any]:
        """Get screenshot configuration with code-based defaults."""
        return {
            "screenshots_dir": Path("./screenshots"),
            "screenshot_format": "png",
        }

    @field_validator("traversals_dir")
    @classmethod
    def create_directories_if_not_exist(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }
