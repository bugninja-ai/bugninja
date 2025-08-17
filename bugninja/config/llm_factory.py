"""
LLM factory pattern using the new deduplicated system.

This module provides a factory pattern for creating LLM instances from different
providers using the new base factory class to eliminate code duplication.
"""

from abc import ABC
from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

from bugninja.config.llm_config import LLMConfig
from bugninja.config.provider_registry import ProviderRegistry
from bugninja.config.settings import BugninjaSettings, LLMProvider

# Protocol and abstract base class are now handled by BaseLLMFactory


# All factory classes are now handled by BaseLLMFactory
# Individual factory classes are no longer needed due to the unified approach


class BaseLLMFactory(ABC):
    """
    Base LLM factory with common functionality.

    This module provides a base factory class that handles common LLM creation logic,
    eliminating duplication across provider-specific factory classes.
    """

    def __init__(self, settings: BugninjaSettings, provider: LLMProvider):
        self.settings = settings
        self.provider = provider
        self.provider_config = ProviderRegistry.get_config(provider)

    def validate_config(self) -> bool:
        """Validate using provider-specific requirements."""
        return self.provider_config.validate_requirements(self.settings)

    def create_model_from_config(self, config: LLMConfig) -> BaseChatModel:
        """Create model using provider-specific configuration."""
        if not self.validate_config():
            raise ValueError(self.provider_config.error_message)

        # Build common configuration
        factory_config = self._build_common_config(config)

        # Add provider-specific configuration
        factory_config.update(self._build_provider_config(config))

        try:
            return self.provider_config.model_class(**factory_config)
        except Exception as e:
            raise ValueError(f"Failed to create {self.provider_config.name} model: {e}")

    def _build_common_config(self, config: LLMConfig) -> Dict[str, Any]:
        """Build common configuration parameters."""
        factory_config: Dict[str, Any] = {
            "model": config.model,
            "temperature": config.temperature,
        }

        # Add optional parameters
        if config.max_tokens:
            factory_config[self.provider_config.max_tokens_param] = config.max_tokens
        if config.timeout:
            factory_config["timeout"] = config.timeout

        return factory_config

    def _build_provider_config(self, config: LLMConfig) -> Dict[str, Any]:
        """Build provider-specific configuration. Override in subclasses if needed."""
        provider_config: Dict[str, Any] = {}

        # Handle API key (except for Ollama)
        if self.provider != LLMProvider.OLLAMA:
            provider_config["api_key"] = self.provider_config.get_api_key(self.settings)

        # Handle base URL
        base_url = self.provider_config.get_base_url(self.settings, config.base_url)
        if base_url:
            if self.provider == LLMProvider.AZURE_OPENAI:
                provider_config["azure_endpoint"] = base_url
            else:
                provider_config["base_url"] = base_url

        # Handle API version (Azure OpenAI specific)
        if self.provider == LLMProvider.AZURE_OPENAI and self.provider_config.api_version_setting:
            api_version = config.api_version or getattr(
                self.settings, self.provider_config.api_version_setting, None
            )
            if api_version:
                provider_config["api_version"] = api_version

        # Handle Google API key (special case)
        if self.provider == LLMProvider.GOOGLE_GEMINI:
            provider_config["google_api_key"] = self.provider_config.get_api_key(self.settings)

        return provider_config


class LLMFactoryRegistry:
    """Registry for LLM factories using the new unified system."""

    @classmethod
    def create_llm_from_config(cls, config: LLMConfig, settings: BugninjaSettings) -> BaseChatModel:
        """Create LLM model from unified configuration.

        Args:
            config: Unified LLM configuration
            settings: BugninjaSettings instance

        Returns:
            Configured LLM model instance

        Raises:
            ValueError: If provider is unsupported or configuration is invalid
        """
        if not ProviderRegistry.is_provider_supported(config.provider):
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

        factory = BaseLLMFactory(settings, config.provider)
        return factory.create_model_from_config(config)
