"""
Configuration factory for managing settings instances.

This module provides a factory pattern for creating and managing configuration
instances with TOML-based configuration and singleton behavior.
"""

from typing import Any, Dict, Optional

from .settings import BugninjaSettings
from .toml_loader import TOMLConfigLoader

# TODO!:AGENT this current configuration factory here does not support multiple AI models to be utilized, and naming conventions also do not reflect on this


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
                error_str = str(e).lower()
                if "azure_openai_endpoint" in error_str or "azure_openai_key" in error_str:
                    raise ValueError(
                        f"Missing required environment variables. Please ensure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY are set in your .env file or environment. "
                        f"Error: {e}"
                    )
                else:
                    raise ValueError(f"Failed to create settings: {e}")

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
            "project.name": "project_name",
            "llm.model": "azure_openai_model",
            "llm.temperature": "azure_openai_temperature",
            "llm.api_version": "azure_openai_api_version",
            "logging.level": "log_level",
            "logging.format": "log_format",
            "logging.enable_rich_logging": "enable_rich_logging",
            "development.debug_mode": "debug_mode",
            "development.enable_verbose_logging": "enable_verbose_logging",
            "paths.traversals_dir": "traversals_dir",
            "events.publishers": "event_publishers",
        }

        pydantic_config = {}
        for toml_key, field_name in field_mapping.items():
            if toml_key in toml_config:
                pydantic_config[field_name] = toml_config[toml_key]

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
            "llm_model": settings.azure_openai_model,
            "llm_temperature": settings.azure_openai_temperature,
            "viewport": {
                "width": settings.browser_config["viewport_width"],
                "height": settings.browser_config["viewport_height"],
            },
            "max_steps": settings.agent_config["max_steps"],
            "debug_mode": settings.debug_mode,
            "log_level": settings.log_level,
            "screenshots_dir": str(settings.screenshot_config["screenshots_dir"]),
        }
