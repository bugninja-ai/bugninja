"""
Core configuration settings for Bugninja using Pydantic Settings.

This module provides type-safe configuration management with environment variable
support, validation, and default values for all Bugninja components.
"""

from pathlib import Path
from typing import Any, Dict

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class BugninjaSettings(BaseSettings):
    """Main configuration settings for Bugninja framework.

    This class provides centralized configuration management with:
    - Type-safe configuration with validation
    - Environment variable support for LLM and logging settings
    - Code-based defaults for browser, agent, and replicator settings
    - Nested configuration support
    """

    # LLM Configuration
    azure_openai_endpoint: str = Field(
        ..., alias="AZURE_OPENAI_ENDPOINT", description="Azure OpenAI endpoint URL"
    )
    azure_openai_key: SecretStr = Field(
        ..., alias="AZURE_OPENAI_KEY", description="Azure OpenAI API key"
    )
    azure_openai_model: str = Field(
        default="gpt-4.1", alias="AZURE_OPENAI_MODEL", description="Azure OpenAI model name"
    )
    azure_openai_temperature: float = Field(
        default=0.001,
        alias="AZURE_OPENAI_TEMPERATURE",
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        alias="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        alias="LOG_FORMAT",
        description="Logging format string",
    )
    enable_rich_logging: bool = Field(
        default=True, alias="ENABLE_RICH_LOGGING", description="Enable rich console logging"
    )

    # Development Configuration
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE", description="Enable debug mode")
    bypass_llm_verification: bool = Field(
        default=False,
        alias="BYPASS_LLM_VERIFICATION",
        description="Bypass LLM verification for testing",
    )
    enable_verbose_logging: bool = Field(
        default=False,
        alias="ENABLE_VERBOSE_LOGGING",
        description="Enable verbose logging for debugging",
    )

    # File Paths Configuration
    traversals_dir: Path = Field(
        default=Path("./traversals"),
        alias="TRAVERSALS_DIR",
        description="Directory for storing traversal files",
    )
    logs_dir: Path = Field(
        default=Path("./logs"), alias="LOGS_DIR", description="Directory for storing log files"
    )

    # Code-based Browser Configuration (not from environment)
    @property
    def browser_config(self) -> Dict[str, Any]:
        """Get browser configuration with code-based defaults."""
        return {
            "viewport_width": 1280,
            "viewport_height": 960,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

    # Code-based Authentication Configuration (not from environment)
    @property
    def authentication_handling_prompt(self) -> str:
        """Get authentication handling prompt with code-based default."""
        return """### HANDLING THIRD PARTY AUTHENTICATION

It is very important that you are able to handle third-party authentication or the non-authentication software, such as applications or SMS verifications, in your action space. There is a declared action for this type of interaction, and you must not forget that you can handle this. In this scenario, you will wait for the user's response, and the user will be signaling when the third-party authentication is completed. After that is done, you must re-evaluate the updated state of the browser."""

    @field_validator("traversals_dir", "logs_dir")
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
        "validate_assignment": True,
        "extra": "ignore",  # Ignore extra fields from environment
    }
