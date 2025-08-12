"""
Utility functions for creating prompt strings from markdown files.

This module provides **functions to read and process prompt templates** from markdown
files for use in the Bugninja framework, with robust handling for both development
and installed package scenarios.

## Key Functions

1. **get_authentication_handling_prompt()** - Load authentication prompt from markdown
2. **AUTHENTICATION_HANDLING_EXTRA_PROMPT** - Pre-loaded authentication prompt constant

## Usage Examples

```python
from bugninja.utils.prompt_string_factories import (
    get_authentication_handling_prompt,
    AUTHENTICATION_HANDLING_EXTRA_PROMPT
)

# Load prompt dynamically
prompt = get_authentication_handling_prompt("third_party_auth_handler_prompt.md")

# Use pre-loaded constant
print(AUTHENTICATION_HANDLING_EXTRA_PROMPT)
```
"""

import importlib.resources
from pathlib import Path


def get_authentication_handling_prompt(prompt_markdown_name: str) -> str:
    """Get the authentication handling prompt from the markdown file.

    This function loads prompt templates from markdown files using a robust
    approach that works both in development and when the package is installed.
    It first tries to use `importlib.resources` for installed packages, then
    falls back to file system paths for development.

    Args:
        prompt_markdown_name (str): Name of the markdown file to load

    Returns:
        str: The authentication handling prompt content as a string

    Raises:
        FileNotFoundError: If the markdown file cannot be found
        IOError: If there's an error reading the markdown file

    Example:
        ```python
        from bugninja.utils.prompt_string_factories import get_authentication_handling_prompt

        # Load authentication prompt
        prompt = get_authentication_handling_prompt("third_party_auth_handler_prompt.md")
        print(prompt)
        ```
    """
    try:
        # First, try to load using importlib.resources (for installed packages)
        with (
            importlib.resources.files("bugninja.prompts")
            .joinpath(prompt_markdown_name)
            .open("r", encoding="utf-8") as file
        ):
            return file.read()
    except (FileNotFoundError, ImportError):
        # Fallback to file system path (for development)
        current_file = Path(__file__)
        prompts_dir = current_file.parent.parent / "prompts"
        prompt_file = prompts_dir / prompt_markdown_name

        try:
            with open(prompt_file, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Markdown file not found: {prompt_file}")
        except IOError as e:
            raise IOError(f"Error reading markdown file {prompt_file}: {e}")


# Legacy constant for backward compatibility
AUTHENTICATION_HANDLING_EXTRA_PROMPT: str = get_authentication_handling_prompt(
    prompt_markdown_name="third_party_auth_handler_prompt.md"
)
