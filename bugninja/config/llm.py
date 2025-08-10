"""
LLM configuration and factory functions.

This module provides functions for creating LLM instances with proper
configuration from the settings system.
"""

from typing import Any, Dict

from langchain_openai import AzureChatOpenAI

from .factory import ConfigurationFactory


# TODO!:AGENT current setup does not reflect on the utilization possibility of multiple LLM models
def create_llm_config() -> Dict[str, Any]:
    """Create LLM configuration from settings.

    Returns:
        Dictionary with LLM configuration parameters

    Raises:
        ValueError: If LLM configuration is invalid
    """
    settings = ConfigurationFactory.get_settings()

    return {
        "model": settings.azure_openai_model,
        "api_version": settings.azure_openai_api_version,
        "azure_endpoint": settings.azure_openai_endpoint,
        "api_key": settings.azure_openai_key,
        "temperature": settings.azure_openai_temperature,
    }


def create_azure_openai_model() -> AzureChatOpenAI:
    """Create Azure OpenAI model with configuration.

    Returns:
        Configured AzureChatOpenAI instance

    Raises:
        ValueError: If LLM configuration is invalid
    """
    config = create_llm_config()

    try:
        return AzureChatOpenAI(**config)
    except Exception as e:
        raise ValueError(f"Failed to create Azure OpenAI model: {e}")
