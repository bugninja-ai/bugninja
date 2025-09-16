"""
Unified LLM model creation utilities.

This module provides unified functions for creating LLM models,
eliminating duplication across provider-specific creation functions.
"""

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from bugninja.config.factory import ConfigurationFactory
from bugninja.config.llm_config import LLMConfig
from bugninja.config.llm_factory import BaseLLMFactory
from bugninja.config.settings import BugninjaSettings, LLMProvider


def create_provider_model(
    provider: LLMProvider,
    temperature: Optional[float] = None,
    settings: Optional[BugninjaSettings] = None,
) -> BaseChatModel:
    """Create LLM model for any provider with unified interface.

    This function replaces all provider-specific model creation functions
    with a single, unified interface that handles all providers.

    Args:
        provider (LLMProvider): LLM provider to use
        temperature (Optional[float]): Optional temperature override
        settings (Optional[BugninjaSettings]): Optional settings instance (uses default if None)

    Returns:
        BaseChatModel: Configured LLM model instance

    Raises:
        ValueError: If provider is unsupported or configuration is invalid

    Example:
        ```python
        from bugninja.config.llm_creator import create_provider_model
        from bugninja.config.settings import LLMProvider

        # Create OpenAI model
        model = create_provider_model(LLMProvider.OPENAI, temperature=0.1)

        # Create Azure OpenAI model with custom settings
        settings = BugninjaSettings()
        model = create_provider_model(LLMProvider.AZURE_OPENAI, settings=settings)
        ```
    """

    # Get settings if not provided
    if settings is None:
        settings = ConfigurationFactory.get_settings()

    # Create factory for the provider
    factory = BaseLLMFactory(settings, provider)

    # Create configuration
    config = LLMConfig.create_default(provider)

    # Override temperature if specified
    if temperature is not None:
        config.temperature = temperature

    # Create and return model
    return factory.create_model_from_config(config)


def create_provider_model_from_settings(
    temperature: Optional[float] = None,
    settings: Optional[BugninjaSettings] = None,
) -> BaseChatModel:
    """Create LLM model using provider from settings.

    Args:
        temperature: Optional temperature override
        settings: Optional settings instance (uses default if None)

    Returns:
        Configured LLM model instance

    Raises:
        ValueError: If configuration is invalid
    """

    # Get settings if not provided
    if settings is None:
        settings = ConfigurationFactory.get_settings()

    # Create model using provider from settings
    return create_provider_model(
        provider=settings.llm_provider,
        temperature=temperature,
        settings=settings,
    )


def create_llm_model_from_config(config: LLMConfig) -> BaseChatModel:
    """Create LLM model from unified configuration.

    Args:
        config: Unified LLM configuration

    Returns:
        Configured LLM model instance

    Raises:
        ValueError: If configuration is invalid
    """

    settings = ConfigurationFactory.get_settings()
    factory = BaseLLMFactory(settings, config.provider)
    return factory.create_model_from_config(config)


def create_llm_config_from_settings() -> LLMConfig:
    """Create LLM configuration from settings.

    Returns:
        LLM configuration based on current settings

    Raises:
        ValueError: If settings are invalid
    """

    settings = ConfigurationFactory.get_settings()
    return LLMConfig.create_default(settings.llm_provider)
