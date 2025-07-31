"""
LLM model configuration using the new settings system.

This module provides LLM model creation functions that use the centralized
configuration management system for type-safe and environment-aware settings.
"""

from typing import Optional

from langchain_openai import AzureChatOpenAI

from ..config import ConfigurationFactory, Environment, create_azure_openai_model


def azure_openai_model(
    temperature: Optional[float] = None, environment: Environment = Environment.DEVELOPMENT
) -> AzureChatOpenAI:
    """Create Azure OpenAI model with configuration.

    Args:
        temperature: Optional temperature override (uses default from settings if None)
        environment: The target environment for configuration

    Returns:
        Configured AzureChatOpenAI instance

    Raises:
        ValueError: If LLM configuration is invalid or missing
    """
    # Get settings for the environment
    settings = ConfigurationFactory.get_settings(environment)

    # Use provided temperature or default from settings
    if temperature is not None:
        settings.azure_openai_temperature = temperature

    # Create and return the model
    return create_azure_openai_model(environment)
