"""
Configuration factory for managing settings instances.

This module provides a factory pattern for creating and managing configuration
instances with environment-specific overrides and singleton behavior.
"""

from typing import Any, Dict, Optional

from .environments import Environment, EnvironmentSettings
from .settings import BugninjaSettings

# TODO!:AGENT this current configuration factory here does not support multiple AI models to be utilized, and naming conventions also do not reflect on this


class ConfigurationFactory:
    """Factory for creating and managing configuration instances.

    This class provides a singleton pattern for configuration management
    with environment-specific overrides and validation.
    """

    _instance: Optional[BugninjaSettings] = None
    _current_environment: Optional[Environment] = None

    @classmethod
    def get_settings(cls, environment: Environment = Environment.DEVELOPMENT) -> BugninjaSettings:
        """Get or create settings instance with environment overrides.

        Args:
            environment: The target environment for configuration

        Returns:
            Configured settings instance

        Raises:
            ValueError: If environment configuration is invalid
        """
        # Check if we need to create a new instance or update existing
        if cls._instance is None or cls._current_environment != environment:
            # Get environment overrides
            overrides = EnvironmentSettings.get_environment_overrides(environment)

            # Create settings with overrides
            try:
                cls._instance = BugninjaSettings(**overrides)
                cls._current_environment = environment
            except Exception as e:
                raise ValueError(f"Failed to create settings for environment {environment}: {e}")

        return cls._instance

    @classmethod
    def get_current_environment(cls) -> Optional[Environment]:
        """Get the current environment.

        Returns:
            Current environment or None if no settings have been created
        """
        return cls._current_environment

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing).

        This method clears the cached settings instance, forcing
        a new instance to be created on the next get_settings() call.
        """
        cls._instance = None
        cls._current_environment = None

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
    def get_settings_summary(
        cls, environment: Environment = Environment.DEVELOPMENT
    ) -> Dict[str, Any]:
        """Get a summary of current settings for the environment.

        Args:
            environment: The target environment

        Returns:
            Dictionary with settings summary
        """
        settings = cls.get_settings(environment)

        return {
            "environment": environment.value,
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
