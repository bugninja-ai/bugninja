"""
Provider configuration registry for LLM factories.

This module provides a centralized registry for provider-specific configurations,
eliminating code duplication across factory classes and error handling.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from bugninja.config.settings import BugninjaSettings, LLMProvider


@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider."""

    name: str
    required_env_vars: List[str]
    error_message: str
    model_class: Type[BaseChatModel]
    api_key_setting: str
    base_url_setting: Optional[str] = None
    api_version_setting: Optional[str] = None
    max_tokens_param: str = "max_tokens"

    def validate_requirements(self, settings: BugninjaSettings) -> bool:
        """Validate that required environment variables are set."""
        for env_var in self.required_env_vars:
            if not hasattr(settings, env_var) or getattr(settings, env_var) is None:
                return False
        return True

    def get_api_key(self, settings: BugninjaSettings) -> str:
        """Get API key from settings."""
        from pydantic import SecretStr

        api_key = getattr(settings, self.api_key_setting, None)
        if api_key is None:
            raise ValueError(f"Missing {self.api_key_setting}")

        if isinstance(api_key, SecretStr):
            return api_key.get_secret_value()
        else:
            return str(api_key)

    def get_base_url(
        self, settings: BugninjaSettings, config_base_url: Optional[str] = None
    ) -> Optional[str]:
        """Get base URL with fallback logic."""
        if config_base_url:
            return config_base_url
        if self.base_url_setting:
            return getattr(settings, self.base_url_setting, None)
        return None


class ProviderRegistry:
    """Registry for provider-specific configurations."""

    _providers: Dict[LLMProvider, ProviderConfig] = {
        LLMProvider.AZURE_OPENAI: ProviderConfig(
            name="Azure OpenAI",
            required_env_vars=["azure_openai_endpoint", "azure_openai_key"],
            error_message="Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY",
            model_class=AzureChatOpenAI,
            api_key_setting="azure_openai_key",
            base_url_setting="azure_openai_endpoint",
            api_version_setting="azure_openai_api_version",
        ),
        LLMProvider.OPENAI: ProviderConfig(
            name="OpenAI",
            required_env_vars=["openai_api_key"],
            error_message="OpenAI requires OPENAI_API_KEY",
            model_class=ChatOpenAI,
            api_key_setting="openai_api_key",
            base_url_setting="openai_base_url",
        ),
        LLMProvider.ANTHROPIC: ProviderConfig(
            name="Anthropic",
            required_env_vars=["anthropic_api_key"],
            error_message="Anthropic requires ANTHROPIC_API_KEY",
            model_class=ChatAnthropic,
            api_key_setting="anthropic_api_key",
            base_url_setting="anthropic_base_url",
        ),
        LLMProvider.GOOGLE_GEMINI: ProviderConfig(
            name="Google Gemini",
            required_env_vars=["google_api_key"],
            error_message="Google Gemini requires GOOGLE_API_KEY",
            model_class=ChatGoogleGenerativeAI,
            api_key_setting="google_api_key",
            base_url_setting="google_base_url",
            max_tokens_param="max_output_tokens",
        ),
        LLMProvider.DEEPSEEK: ProviderConfig(
            name="DeepSeek",
            required_env_vars=["deepseek_api_key"],
            error_message="DeepSeek requires DEEPSEEK_API_KEY",
            model_class=ChatDeepSeek,
            api_key_setting="deepseek_api_key",
            base_url_setting="deepseek_base_url",
        ),
        LLMProvider.OLLAMA: ProviderConfig(
            name="Ollama",
            required_env_vars=[],  # Ollama doesn't require API key
            error_message="Ollama configuration error",
            model_class=ChatOllama,
            api_key_setting="",  # Not used for Ollama
            base_url_setting="ollama_base_url",
            max_tokens_param="num_predict",
        ),
    }

    @classmethod
    def get_config(cls, provider: LLMProvider) -> ProviderConfig:
        """Get configuration for a provider."""
        config = cls._providers.get(provider)
        if not config:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return config

    @classmethod
    def get_supported_providers(cls) -> List[LLMProvider]:
        """Get list of supported providers."""
        return list(cls._providers.keys())

    @classmethod
    def is_provider_supported(cls, provider: LLMProvider) -> bool:
        """Check if provider is supported."""
        return provider in cls._providers
