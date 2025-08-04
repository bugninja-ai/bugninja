"""
Utility functions for creating prompt strings from markdown files.

This module provides functions to read and process prompt templates
from markdown files for use in the Bugninja framework.
"""

from pathlib import Path


def get_authentication_handling_prompt(prompt_markdown_name: str) -> str:
    """
    Get the authentication handling prompt from the markdown file.

    Returns:
        The authentication handling prompt content as a string
    """
    # Get the path to the prompts directory relative to this file
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
