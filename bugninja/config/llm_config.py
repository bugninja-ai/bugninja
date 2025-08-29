"""
Unified LLM configuration model for fine-grained control.

This module provides a robust configuration system for LLM providers,
models, and parameters with validation and provider-specific defaults.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from bugninja.config.settings import LLMProvider


@dataclass
class LLMConfig:
    """Unified LLM configuration model with validation.

    This class provides fine-grained control over LLM configuration
    including provider, model, temperature, and other parameters.
    """

    provider: LLMProvider
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate provider-model compatibility and parameters.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate provider
        if not isinstance(self.provider, LLMProvider):
            raise ValueError(f"Invalid provider: {self.provider}")

        # Validate model compatibility
        supported_models = ModelRegistry.get_supported_models(self.provider)
        if self.model not in supported_models:
            raise ValueError(
                f"Model '{self.model}' not supported for provider '{self.provider.value}'. "
                f"Supported models: {', '.join(supported_models)}"
            )

        # Validate temperature
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}")

        # Validate max_tokens
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")

        # Validate timeout
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

    @classmethod
    def create_default(cls, provider: LLMProvider) -> "LLMConfig":
        """Create default configuration for a provider.

        Args:
            provider: LLM provider to create default config for

        Returns:
            LLMConfig with provider-specific defaults
        """
        default_model = ModelRegistry.get_default_model(provider)
        return cls(provider=provider, model=default_model)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "provider": self.provider.value,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": self.base_url,
            "api_version": self.api_version,
            "custom_headers": self.custom_headers,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary containing configuration data

        Returns:
            LLMConfig instance

        Raises:
            ValueError: If data is invalid
        """
        try:
            provider = LLMProvider(data["provider"])
            return cls(
                provider=provider,
                model=data["model"],
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens"),
                base_url=data.get("base_url"),
                api_version=data.get("api_version"),
                custom_headers=data.get("custom_headers"),
                timeout=data.get("timeout"),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid configuration data: {e}")


class ModelRegistry:
    """Registry of supported models per provider with validation."""

    # Supported models for each provider
    SUPPORTED_MODELS: Dict[LLMProvider, Set[str]] = {
        LLMProvider.AZURE_OPENAI: {
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-5",
            "gpt-5-mini",
        },
        LLMProvider.OPENAI: {
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-5",
            "gpt-5-mini",
        },
        LLMProvider.GOOGLE_GEMINI: {
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            # 2.0
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash-live-001",
        },
        LLMProvider.ANTHROPIC: {
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        },
        LLMProvider.DEEPSEEK: {
            "deepseek-chat",
            "deepseek-coder",
        },
        LLMProvider.OLLAMA: {
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "codellama",
            "mistral",
            "mixtral",
        },
    }

    # Default models for each provider
    DEFAULT_MODELS: Dict[LLMProvider, str] = {
        LLMProvider.AZURE_OPENAI: "gpt-4",
        LLMProvider.OPENAI: "gpt-4",
        LLMProvider.GOOGLE_GEMINI: "gemini-1.5-pro",
        LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
        LLMProvider.DEEPSEEK: "deepseek-chat",
        LLMProvider.OLLAMA: "llama2",
    }

    @classmethod
    def get_supported_models(cls, provider: LLMProvider) -> Set[str]:
        """Get supported models for a provider.

        Args:
            provider: LLM provider

        Returns:
            Set of supported model names

        Raises:
            ValueError: If provider is not supported
        """
        if provider not in cls.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported provider: {provider}")
        return cls.SUPPORTED_MODELS[provider]

    @classmethod
    def get_default_model(cls, provider: LLMProvider) -> str:
        """Get default model for a provider.

        Args:
            provider: LLM provider

        Returns:
            Default model name

        Raises:
            ValueError: If provider is not supported
        """
        if provider not in cls.DEFAULT_MODELS:
            raise ValueError(f"Unsupported provider: {provider}")
        return cls.DEFAULT_MODELS[provider]

    @classmethod
    def is_model_supported(cls, provider: LLMProvider, model: str) -> bool:
        """Check if a model is supported for a provider.

        Args:
            provider: LLM provider
            model: Model name to check

        Returns:
            True if model is supported, False otherwise
        """
        try:
            return model in cls.get_supported_models(provider)
        except ValueError:
            return False

    @classmethod
    def list_providers(cls) -> List[LLMProvider]:
        """Get list of all supported providers.

        Returns:
            List of supported LLM providers
        """
        return list(cls.SUPPORTED_MODELS.keys())

    @classmethod
    def get_provider_info(cls, provider: LLMProvider) -> Dict[str, Any]:
        """Get detailed information about a provider.

        Args:
            provider: LLM provider

        Returns:
            Dictionary with provider information

        Raises:
            ValueError: If provider is not supported
        """
        if provider not in cls.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported provider: {provider}")

        return {
            "provider": provider.value,
            "supported_models": list(cls.SUPPORTED_MODELS[provider]),
            "default_model": cls.DEFAULT_MODELS[provider],
            "model_count": len(cls.SUPPORTED_MODELS[provider]),
        }
