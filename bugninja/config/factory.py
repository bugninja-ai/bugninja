"""
Configuration factory for managing settings instances.

This module provides a factory pattern for creating and managing configuration
instances with TOML-based configuration and singleton behavior.
"""

import os
from typing import Any, Dict, Optional

from bugninja.config.settings import BugninjaSettings, LLMProvider
from bugninja.config.toml_loader import TOMLConfigLoader


class ConfigurationFactory:
    """Factory for creating and managing configuration instances.

    This class provides a singleton pattern for configuration management
    with TOML-based configuration and validation.
    """

    _instance: Optional[BugninjaSettings] = None
    _toml_loader: Optional[TOMLConfigLoader] = None

    @classmethod
    def get_settings(cls) -> BugninjaSettings:
        """Get or create settings instance.

        Returns:
            Configured settings instance

        Raises:
            ValueError: If configuration is invalid
        """
        # Check if we need to create a new instance
        if cls._instance is None:
            # Initialize TOML loader if needed
            if cls._toml_loader is None:
                cls._toml_loader = TOMLConfigLoader()

            # Try to load TOML configuration first
            toml_overrides = {}
            try:
                toml_config = cls._toml_loader.load_config()
                toml_overrides = cls._convert_toml_to_pydantic(toml_config)
            except Exception:
                # If TOML loading fails, continue without TOML overrides
                # This allows backward compatibility when TOML file is missing
                pass

            # Create settings with TOML overrides (if any)
            # BugninjaSettings() will automatically load from environment variables
            try:
                cls._instance = BugninjaSettings(**toml_overrides)
            except Exception as e:
                # Provide more helpful error message for missing environment variables
                # Simplified error handling to avoid constructor issues
                raise ValueError(
                    f"Configuration error. Please check your environment variables. Original error: {str(e).lower()}"
                )

        return cls._instance

    @classmethod
    def _convert_toml_to_pydantic(cls, toml_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TOML configuration to Pydantic-compatible format.

        Args:
            toml_config: Flattened TOML configuration

        Returns:
            Dictionary compatible with Pydantic Settings
        """
        field_mapping = {
            # Project configuration
            "project.name": "project_name",
            # LLM configuration
            "llm.provider": "llm_provider",
            "llm.model": "llm_model",
            "llm.temperature": "llm_temperature",
            # Azure OpenAI configuration
            "llm.azure_openai.api_version": "azure_openai_api_version",
            # OpenAI configuration
            "llm.openai.base_url": "openai_base_url",
            # Anthropic configuration
            "llm.anthropic.base_url": "anthropic_base_url",
            # Google Gemini configuration
            "llm.google_gemini.base_url": "google_base_url",
            # DeepSeek configuration
            "llm.deepseek.base_url": "deepseek_base_url",
            # Ollama configuration
            "llm.ollama.base_url": "ollama_base_url",
            # Logging configuration
            "logging.level": "log_level",
            "logging.format": "log_format",
            "logging.enable_rich_logging": "enable_rich_logging",
            # Development configuration
            "development.debug_mode": "debug_mode",
            "development.enable_verbose_logging": "enable_verbose_logging",
            # Paths configuration
            "paths.traversals_dir": "traversals_dir",
            "paths.screenshots_dir": "screenshots_dir",
            "paths.tasks_dir": "tasks_dir",
            # Events configuration
            "events.publishers": "event_publishers",
        }

        pydantic_config = {}
        for toml_key, field_name in field_mapping.items():
            if toml_key in toml_config:
                value = toml_config[toml_key]

                # Handle special cases
                if toml_key == "llm.provider" and isinstance(value, str):
                    # Convert string to LLMProvider enum
                    try:
                        value = LLMProvider(value)
                    except ValueError:
                        # Skip invalid provider values
                        continue
                elif toml_key.startswith("paths.") and isinstance(value, str):
                    # Convert string paths to Path objects
                    from pathlib import Path

                    value = Path(value)

                pydantic_config[field_name] = value

        # Add environment variable fallbacks for base URLs
        config_name_env_var_assoc: Dict[str, str] = {
            "openai_base_url": "OPENAI_BASE_URL",
            "anthropic_base_url": "ANTHROPIC_BASE_URL",
            "google_base_url": "GOOGLE_BASE_URL",
            "deepseek_base_url": "DEEPSEEK_BASE_URL",
            "ollama_base_url": "OLLAMA_BASE_URL",
        }

        for config_name, env_Var_name in config_name_env_var_assoc.items():
            if config_name not in pydantic_config and os.getenv(env_Var_name):
                pydantic_config[config_name] = os.getenv(env_Var_name)

        return pydantic_config

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing).

        This method clears the cached settings instance and TOML loader, forcing
        a new instance to be created on the next get_settings() call.
        """
        cls._instance = None
        cls._toml_loader = None

    @classmethod
    def validate_settings(cls, settings: BugninjaSettings) -> bool:
        """Validate settings instance.

        Args:
            settings: Settings instance to validate

        Returns:
            True if settings are valid
        """
        try:
            # This will raise validation errors if settings are invalid
            settings.model_validate(settings.model_dump())
            return True
        except Exception:
            return False

    @classmethod
    def get_settings_summary(cls) -> Dict[str, Any]:
        """Get a summary of current settings.

        Returns:
            Dictionary with settings summary
        """
        settings = cls.get_settings()

        return {
            "project_name": settings.project_name,
            "llm_provider": settings.llm_provider.value,
            "llm_model": settings.llm_model,
            "llm_temperature": settings.llm_temperature,
            "viewport": {
                "width": settings.browser_config["viewport_width"],
                "height": settings.browser_config["viewport_height"],
            },
            "max_steps": settings.agent_config["max_steps"],
            "debug_mode": settings.debug_mode,
            "log_level": settings.log_level,
            "screenshots_dir": str(settings.screenshot_config["screenshots_dir"]),
        }
