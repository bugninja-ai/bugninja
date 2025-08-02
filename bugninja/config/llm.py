"""
LLM configuration and factory functions.

This module provides functions for creating LLM instances with proper
configuration from the settings system.
"""

from typing import Any, Dict

from langchain_openai import AzureChatOpenAI

from .environments import Environment
from .factory import ConfigurationFactory


def create_llm_config(environment: Environment = Environment.DEVELOPMENT) -> Dict[str, Any]:
    """Create LLM configuration from settings.

    Args:
        environment: The target environment for configuration

    Returns:
        Dictionary with LLM configuration parameters

    Raises:
        ValueError: If LLM configuration is invalid
    """
    settings = ConfigurationFactory.get_settings(environment)

    return {
        "model": settings.azure_openai_model,
        "api_version": settings.azure_openai_api_version,
        "azure_endpoint": settings.azure_openai_endpoint,
        "api_key": settings.azure_openai_key,
        "temperature": settings.azure_openai_temperature,
    }


def create_azure_openai_model(
    environment: Environment = Environment.DEVELOPMENT,
) -> AzureChatOpenAI:
    """Create Azure OpenAI model with configuration.

    Args:
        environment: The target environment for configuration

    Returns:
        Configured AzureChatOpenAI instance

    Raises:
        ValueError: If LLM configuration is invalid
    """
    config = create_llm_config(environment)

    try:
        return AzureChatOpenAI(**config)
    except Exception as e:
        raise ValueError(f"Failed to create Azure OpenAI model: {e}")
