"""
Environment-specific configuration management.

This module provides environment-specific configuration overrides and management
for different deployment scenarios (development, testing, staging, production).
"""

from enum import Enum
from typing import Any, Dict

# TODO!:AGENT environment support this way may be an unnecessary overkill


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Create Environment from string value."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid environment: {value}. Must be one of {[e.value for e in cls]}"
            )


class EnvironmentSettings:
    """Environment-specific configuration overrides."""

    @staticmethod
    def get_environment_overrides(env: Environment) -> Dict[str, Any]:
        """Get configuration overrides for specific environment.

        Args:
            env: The target environment

        Returns:
            Dictionary of configuration overrides for the environment
        """
        overrides = {
            Environment.DEVELOPMENT: {
                "debug_mode": True,
                "log_level": "DEBUG",
                "bypass_llm_verification": True,
                "enable_verbose_logging": True,
                "enable_rich_logging": True,
            },
            Environment.TESTING: {
                "debug_mode": True,
                "log_level": "DEBUG",
                "bypass_llm_verification": True,
                "enable_verbose_logging": True,
            },
            Environment.STAGING: {
                "debug_mode": False,
                "log_level": "INFO",
                "bypass_llm_verification": False,
                "enable_verbose_logging": False,
                "enable_rich_logging": True,
            },
            Environment.PRODUCTION: {
                "debug_mode": False,
                "log_level": "WARNING",
                "bypass_llm_verification": False,
                "enable_verbose_logging": False,
                "enable_rich_logging": False,
            },
        }

        return overrides.get(env, {})
