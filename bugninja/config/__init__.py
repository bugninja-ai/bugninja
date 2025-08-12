"""
Configuration management for Bugninja framework.

This module provides **comprehensive configuration management** with:
- TOML-based configuration with validation
- Factory pattern for configuration creation
- Type-safe configuration with Pydantic models
- Environment variable support for sensitive data
- Code-based defaults for missing values

## Key Components

1. **ConfigurationFactory** - Factory for creating and managing configuration instances
2. **BugninjaSettings** - Main configuration settings with validation
3. **TOMLConfigLoader** - TOML file loading and parsing
4. **create_azure_openai_model** - LLM model creation utility

## Usage Examples

```python
from bugninja.config import ConfigurationFactory, BugninjaSettings

# Get settings with automatic TOML loading
settings = ConfigurationFactory.get_settings()

# Create Azure OpenAI model
from bugninja.config import create_azure_openai_model
llm = create_azure_openai_model(temperature=0.1)
```
"""

from .factory import ConfigurationFactory
from .settings import BugninjaSettings
from .toml_loader import TOMLConfigLoader
from .llm import create_azure_openai_model

__all__ = [
    "ConfigurationFactory",
    "BugninjaSettings",
    "TOMLConfigLoader",
    "create_azure_openai_model",
]
