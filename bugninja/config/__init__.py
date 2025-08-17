"""
Configuration management for Bugninja framework.

This module provides **comprehensive configuration management** with:
- TOML-based configuration with validation
- Factory pattern for configuration creation
- Type-safe configuration with Pydantic models
- Environment variable support for sensitive data
- Code-based defaults for missing values
- Multi-LLM provider support with unified configuration

## Key Components

1. **ConfigurationFactory** - Factory for creating and managing configuration instances
2. **BugninjaSettings** - Main configuration settings with validation
3. **TOMLConfigLoader** - TOML file loading and parsing
4. **LLMProvider** - Enumeration of supported LLM providers
5. **LLMConfig** - Unified LLM configuration dataclass
6. **ModelRegistry** - Provider-specific model validation and defaults
7. **create_llm_model_from_config** - Unified LLM model creation

## Usage Examples

```python
from bugninja.config import ConfigurationFactory, BugninjaSettings, LLMProvider

# Get settings with automatic TOML loading
settings = ConfigurationFactory.get_settings()

# Use unified LLM configuration
from bugninja.config import LLMConfig, LLMProvider, create_llm_model_from_config
config = LLMConfig(provider=LLMProvider.GOOGLE_GEMINI, model="gemini-1.5-pro")
llm = create_llm_model_from_config(config)

# Create from settings
from bugninja.config import create_llm_config_from_settings, create_llm_model_from_config
config = create_llm_config_from_settings()
llm = create_llm_model_from_config(config)
```
"""

from .factory import ConfigurationFactory
from .settings import BugninjaSettings, LLMProvider
from .toml_loader import TOMLConfigLoader
from .llm_creator import (
    create_provider_model,
    create_provider_model_from_settings,
    create_llm_model_from_config,
    create_llm_config_from_settings,
    azure_openai_model,
    openai_model,
    anthropic_model,
    google_gemini_model,
    deepseek_model,
    ollama_model,
)
from .llm_factory import LLMFactoryRegistry
from .llm_config import LLMConfig, ModelRegistry
from .provider_registry import ProviderRegistry
from .error_handler import ConfigurationErrorHandler

__all__ = [
    "ConfigurationFactory",
    "BugninjaSettings",
    "LLMProvider",
    "LLMConfig",
    "ModelRegistry",
    "TOMLConfigLoader",
    "create_provider_model",
    "create_provider_model_from_settings",
    "create_llm_model_from_config",
    "create_llm_config_from_settings",
    "azure_openai_model",
    "openai_model",
    "anthropic_model",
    "google_gemini_model",
    "deepseek_model",
    "ollama_model",
    "ProviderRegistry",
    "ConfigurationErrorHandler",
]
