"""
Configuration management for Bugninja framework.

This module provides configuration management with:
- Environment-based settings
- Factory pattern for configuration creation
- Type-safe configuration with validation
"""

from .environments import Environment
from .factory import ConfigurationFactory
from .settings import BugninjaSettings
from .llm import create_azure_openai_model

__all__ = [
    "Environment",
    "ConfigurationFactory",
    "BugninjaSettings",
    "create_azure_openai_model",
]
