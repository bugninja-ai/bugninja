"""
Core configuration settings for Bugninja using Pydantic Settings.

This module provides type-safe configuration management with TOML file support
for project settings and environment variables for sensitive data, validation,
and default values for all Bugninja components.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bugninja.events.types import EventPublisherType


class LLMProvider(str, Enum):
    """Enumeration of supported LLM providers."""

    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "google_gemini"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


class BugninjaSettings(BaseSettings):
    """Main configuration settings for Bugninja framework.

    This class provides centralized configuration management with:
    - Type-safe configuration with validation
    - TOML file support for project settings
    - Environment variable support for sensitive data (API keys, passwords)
    - Code-based defaults for missing values
    - Nested configuration support
    - Multi-LLM provider support
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # LLM Provider Selection (from TOML)
    llm_provider: LLMProvider = Field(description="LLM provider to use for browser automation")
    llm_temperature: float = Field(
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses",
    )

    # Azure OpenAI Configuration (Sensitive - from .env)
    azure_openai_endpoint: Optional[str] = Field(
        default=None, alias="AZURE_OPENAI_ENDPOINT", description="Azure OpenAI endpoint URL"
    )
    azure_openai_key: Optional[SecretStr] = Field(
        default=None, alias="AZURE_OPENAI_KEY", description="Azure OpenAI API key"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version",
    )

    # OpenAI Configuration (Sensitive - from .env)
    openai_api_key: Optional[SecretStr] = Field(
        default=None, alias="OPENAI_API_KEY", description="OpenAI API key"
    )
    openai_base_url: Optional[str] = Field(
        default=None, description="OpenAI API base URL (from TOML or env)"
    )

    # Anthropic Configuration (Sensitive - from .env)
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None, alias="ANTHROPIC_API_KEY", description="Anthropic API key"
    )
    anthropic_base_url: Optional[str] = Field(
        default=None, description="Anthropic API base URL (from TOML or env)"
    )

    # Google Gemini Configuration (Sensitive - from .env)
    google_api_key: Optional[SecretStr] = Field(
        default=None, alias="GOOGLE_API_KEY", description="Google API key for Gemini"
    )
    google_base_url: Optional[str] = Field(
        default=None, description="Google API base URL (from TOML or env)"
    )

    # DeepSeek Configuration (Sensitive - from .env)
    deepseek_api_key: Optional[SecretStr] = Field(
        default=None, alias="DEEPSEEK_API_KEY", description="DeepSeek API key"
    )
    deepseek_base_url: Optional[str] = Field(
        default=None, description="DeepSeek API base URL (from TOML or env)"
    )

    # Ollama Configuration (from .env)
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama base URL (from TOML or env)"
    )

    # Event Publisher Configuration (from TOML)
    event_publishers: List[EventPublisherType] = Field(
        default=[EventPublisherType.NULL], description="List of event publisher types to use"
    )

    # Logging Configuration (from TOML)
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    enable_rich_logging: bool = Field(default=True, description="Enable rich terminal logging")
    logging_enabled: bool = Field(default=False, description="Enable Bugninja-specific logging")

    # Development Configuration (from TOML)
    debug_mode: bool = Field(default=False, description="Enable debug mode")

    # Project Configuration (from TOML)
    project_name: str = Field(default="bugninja", description="Project name")

    # Paths Configuration (from TOML)
    traversals_dir: Path = Field(
        default=Path("./traversals"), description="Directory for traversal files"
    )
    screenshots_dir: Path = Field(
        default=Path("./screenshots"), description="Directory for screenshots"
    )
    tasks_dir: Path = Field(default=Path("./tasks"), description="Directory for task files")

    # Agent Configuration (from TOML)
    agent_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_steps": 100,
            "planner_interval": 5,
            "enable_vision": True,
            "wait_between_actions": 1.0,
        },
        description="Agent configuration settings",
    )

    # Screenshot Configuration (from TOML)
    screenshot_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "screenshots_dir": Path("./screenshots"),
            "format": "png",
        },
        description="Screenshot configuration settings",
    )

    # Replicator Configuration (from TOML)
    replicator_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "sleep_after_actions": 1.0,
            "pause_after_each_step": True,
            "fail_on_unimplemented_action": False,
            "max_retries": 2,
            "retry_delay": 0.5,
        },
        description="Replicator configuration settings",
    )

    # Jira Configuration (from TOML and .env)
    jira_server: Optional[str] = Field(
        default=None, alias="JIRA_SERVER", description="Jira server base URL"
    )
    jira_user: Optional[str] = Field(
        default=None, alias="JIRA_USER", description="Jira user email (for Cloud) or username"
    )
    jira_api_token: Optional[SecretStr] = Field(
        default=None, alias="JIRA_API_TOKEN", description="Jira API token or Personal Access Token"
    )
    jira_project_key: Optional[str] = Field(
        default=None, description="Jira project key where issues will be created"
    )
    jira_assignees: List[str] = Field(
        default_factory=list, description="List of Jira user names to assign tickets to"
    )

    # Redmine Configuration (from TOML and .env)
    redmine_server: Optional[str] = Field(
        default=None, alias="REDMINE_SERVER", description="Redmine server base URL"
    )
    redmine_api_key: Optional[SecretStr] = Field(
        default=None, alias="REDMINE_API_KEY", description="Redmine API key (preferred auth method)"
    )
    redmine_user: Optional[str] = Field(
        default=None, alias="REDMINE_USER", description="Redmine username (alternative auth)"
    )
    redmine_password: Optional[SecretStr] = Field(
        default=None, alias="REDMINE_PASSWORD", description="Redmine password (alternative auth)"
    )
    redmine_project_id: Optional[str] = Field(
        default=None, description="Redmine project identifier (can be ID or identifier string)"
    )
    redmine_tracker_id: Optional[int] = Field(
        default=None, description="Tracker ID for issues (e.g., Bug tracker)"
    )
    redmine_assignees: List[str] = Field(
        default_factory=list, description="List of Redmine user IDs or usernames"
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: LLMProvider) -> LLMProvider:
        """Validate LLM provider selection."""
        if v not in LLMProvider:
            raise ValueError(f"Unsupported LLM provider: {v}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization setup (validation moved to lazy validation)."""
        pass

    def _validate_provider_config(self) -> None:
        """Validate that required configuration is present for the selected provider."""

        match self.llm_provider:
            case LLMProvider.AZURE_OPENAI:
                if not self.azure_openai_endpoint or not self.azure_openai_key:
                    raise ValueError(
                        "Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables"
                    )
            case LLMProvider.OPENAI:
                if not self.openai_api_key:
                    raise ValueError("OpenAI requires OPENAI_API_KEY environment variable")
            case LLMProvider.ANTHROPIC:
                if not self.anthropic_api_key:
                    raise ValueError("Anthropic requires ANTHROPIC_API_KEY environment variable")
            case LLMProvider.GOOGLE_GEMINI:
                if not self.google_api_key:
                    raise ValueError("Google Gemini requires GOOGLE_API_KEY environment variable")
            case LLMProvider.DEEPSEEK:
                if not self.deepseek_api_key:
                    raise ValueError("DeepSeek requires DEEPSEEK_API_KEY environment variable")
            case _:
                # Ollama doesn't require API key validation as it's typically local
                pass

    # Backward compatibility properties
    @property
    def azure_openai_temperature(self) -> float:
        """Backward compatibility: Get Azure OpenAI temperature."""
        return self.llm_temperature
