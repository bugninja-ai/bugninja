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
    cli_mode: bool = False,
    settings: Optional[BugninjaSettings] = None,
) -> BaseChatModel:
    """Create LLM model for any provider with unified interface.

    This function replaces all provider-specific model creation functions
    with a single, unified interface that handles all providers.

    Args:
        provider (LLMProvider): LLM provider to use
        cli_mode (bool): Whether to use CLI mode (TOML) or Library mode (env vars)
        settings (Optional[BugninjaSettings]): Optional settings instance (uses default if None)

    Returns:
        BaseChatModel: Configured LLM model instance

    Raises:
        ValueError: If provider is unsupported or configuration is invalid

    Example:
        ```python
        from bugninja.config.llm_creator import create_provider_model
        from bugninja.config.settings import LLMProvider

        # Create OpenAI model (Library mode)
        model = create_provider_model(LLMProvider.OPENAI, cli_mode=False)

        # Create Azure OpenAI model (CLI mode)
        model = create_provider_model(LLMProvider.AZURE_OPENAI, cli_mode=True)
        ```
    """

    # Get settings if not provided
    if settings is None:
        settings = ConfigurationFactory.get_settings(cli_mode=cli_mode)

    # Create factory for the provider
    factory = BaseLLMFactory(settings, provider)

    # Create configuration with temperature from settings
    config = LLMConfig.create_default(provider)
    config.temperature = settings.llm_temperature

    # Create and return model
    return factory.create_model_from_config(config)


def create_provider_model_from_settings(
    cli_mode: bool = False,
    settings: Optional[BugninjaSettings] = None,
) -> BaseChatModel:
    """Create LLM model using provider from settings.

    Args:
        cli_mode (bool): Whether to use CLI mode (TOML) or Library mode (env vars)
        settings: Optional settings instance (uses default if None)

    Returns:
        Configured LLM model instance

    Raises:
        ValueError: If configuration is invalid
    """

    # Get settings if not provided
    if settings is None:
        settings = ConfigurationFactory.get_settings(cli_mode=cli_mode)

    # Validate provider configuration
    settings._validate_provider_config()

    # Create model using provider from settings
    return create_provider_model(
        provider=settings.llm_provider,
        cli_mode=cli_mode,
        settings=settings,
    )


def create_llm_model_from_config(config: LLMConfig, cli_mode: bool = False) -> BaseChatModel:
    """Create LLM model from unified configuration.

    Args:
        config: Unified LLM configuration
        cli_mode (bool): Whether to use CLI mode (TOML) or Library mode (env vars)

    Returns:
        Configured LLM model instance

    Raises:
        ValueError: If configuration is invalid
    """

    settings = ConfigurationFactory.get_settings(cli_mode=cli_mode)
    factory = BaseLLMFactory(settings, config.provider)
    return factory.create_model_from_config(config)


def create_llm_config_from_settings(cli_mode: bool = False) -> LLMConfig:
    """Create LLM configuration from settings.

    Args:
        cli_mode (bool): Whether to use CLI mode (TOML) or Library mode (env vars)

    Returns:
        LLM configuration based on current settings

    Raises:
        ValueError: If settings are invalid
    """

    settings = ConfigurationFactory.get_settings(cli_mode=cli_mode)
    return LLMConfig.create_default(settings.llm_provider)
