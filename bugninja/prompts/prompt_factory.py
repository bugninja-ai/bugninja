"""
Prompt factory for Bugninja framework.

This module provides utilities for loading and processing markdown prompt templates
with dynamic variable substitution. It handles both installed package resources
and development file system access for prompt templates.

## Key Functions

1. **__get_raw_prompt()** - Load raw markdown prompt from file
2. **__parsed_prompt()** - Parse prompt with variable substitution
3. **get_extra_instructions_related_prompt()** - Generate extra instructions prompt
4. **get_passed_brainstates_related_prompt()** - Generate brain states prompt

## Template Variables

Templates support variable substitution using `[[VARIABLE_NAME]]` syntax.
Variables are replaced with provided values during prompt generation.

## Usage Examples

```python
from bugninja.prompts.prompt_factory import (
    get_extra_instructions_related_prompt,
    get_passed_brainstates_related_prompt
)

# Generate extra instructions prompt
extra_prompt = get_extra_instructions_related_prompt([
    "Be careful with forms",
    "Take screenshots"
])

# Generate brain states prompt
brain_states_prompt = get_passed_brainstates_related_prompt(completed_brain_states)
```
"""

import importlib.resources
import json
from pathlib import Path
from typing import Dict, List

from bugninja.schemas.pipeline import BugninjaBrainState


def __get_raw_prompt(prompt_markdown_name: str) -> str:
    """Load raw markdown prompt from file.

    Args:
        prompt_markdown_name (str): Name of the markdown file to load

    Returns:
        str: Raw markdown content from the file

    Raises:
        FileNotFoundError: If the markdown file is not found
        IOError: If there's an error reading the file

    Example:
        ```python
        raw_prompt = __get_raw_prompt("navigator_agent_system_prompt.md")
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


def __parsed_prompt(prompt_markdown_name: str, key_value_pairs: Dict[str, str]) -> str:
    """Parse prompt template with variable substitution.

    Args:
        prompt_markdown_name (str): Name of the markdown template file
        key_value_pairs (Dict[str, str]): Dictionary of variable substitutions

    Returns:
        str: Parsed prompt with variables replaced

    Example:
        ```python
        parsed = __parsed_prompt(
            "template.md",
            {"VARIABLE_NAME": "replacement_value"}
        )
        ```
    """
    raw_prompt: str = __get_raw_prompt(prompt_markdown_name)
    for k, v in key_value_pairs.items():
        raw_prompt = raw_prompt.replace(f"[[{k.upper()}]]", v)

    return raw_prompt


#! -------------------------


def get_extra_instructions_related_prompt(extra_instruction_list: List[str]) -> str:
    """Generate extra instructions prompt from instruction list.

    Args:
        extra_instruction_list (List[str]): List of extra instructions to include

    Returns:
        str: Formatted prompt with extra instructions, or empty string if list is empty

    Example:
        ```python
        prompt = get_extra_instructions_related_prompt([
            "Be careful with forms",
            "Take screenshots"
        ])
        ```
    """
    if not extra_instruction_list:
        return ""

    return __parsed_prompt(
        "extra_instructions_prompt.md",
        {"LIST_OF_INSTRUCTIONS": "\n- " + "\n- ".join(extra_instruction_list)},
    )


def get_passed_brainstates_related_prompt(completed_brain_states: List[BugninjaBrainState]) -> str:
    """Generate brain states prompt from completed brain states.

    Args:
        completed_brain_states (List[BugninjaBrainState]): List of completed brain states

    Returns:
        str: Formatted prompt with brain states, or empty string if list is empty

    Example:
        ```python
        prompt = get_passed_brainstates_related_prompt(completed_brain_states)
        ```
    """
    if not completed_brain_states:
        return ""

    return __parsed_prompt(
        "healer_agent_passed_brainstates_prompt.md",
        {
            "COMPLETED_BRAIN_STATES": "\n\n".join(
                [
                    json.dumps(cbs.model_dump(exclude={"id"}), indent=4, ensure_ascii=False)
                    for cbs in completed_brain_states
                ]
            )
        },
    )


BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="navigator_agent_system_prompt.md"
)

HEALDER_AGENT_EXTRA_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="healer_agent_extra_sytem_prompt.md"
)
