"""
Model configurations for Bugninja framework.

This module provides **LLM model configurations** and utilities for:
- Azure OpenAI model creation and configuration
- Model parameter management
- Temperature and other model settings

## Key Components

1. **azure_openai_model** - Factory function for creating Azure OpenAI models
2. **create_llm_config** - LLM configuration creation utility

## Usage Examples

```python
from bugninja.models import azure_openai_model

# Create model with default settings
llm = azure_openai_model()

# Create model with custom temperature
llm = azure_openai_model(temperature=0.1)
```
"""

from .model_configs import azure_openai_model

__all__ = ["azure_openai_model"]
