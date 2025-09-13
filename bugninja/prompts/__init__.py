"""
Bugninja prompt templates and factory.

This package contains markdown prompt templates and prompt generation utilities
used by the Bugninja framework for various automation scenarios and user interactions.

## Key Components

1. **Prompt Factory Functions** - Functions for generating dynamic prompts from templates
2. **System Prompts** - Pre-defined system prompts for different agent types
3. **Template Variables** - Dynamic prompt generation with variable substitution

## Usage Examples

```python
from bugninja.prompts import (
    get_extra_instructions_related_prompt,
    get_passed_brainstates_related_prompt,
    BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
    HEALDER_AGENT_EXTRA_SYSTEM_PROMPT
)

# Generate extra instructions prompt
extra_prompt = get_extra_instructions_related_prompt(["Be careful with forms", "Take screenshots"])

# Generate brain states prompt
brain_states_prompt = get_passed_brainstates_related_prompt(completed_brain_states)

# Use system prompts
navigator_prompt = BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT
healer_prompt = HEALDER_AGENT_EXTRA_SYSTEM_PROMPT
```
"""

from .prompt_factory import (
    BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
    HEALDER_AGENT_EXTRA_SYSTEM_PROMPT,
    get_extra_instructions_related_prompt,
    get_passed_brainstates_related_prompt,
)

__all__ = [
    "get_extra_instructions_related_prompt",
    "get_passed_brainstates_related_prompt",
    "BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT",
    "HEALDER_AGENT_EXTRA_SYSTEM_PROMPT",
]
