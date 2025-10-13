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
from typing import Any, Dict, List

from bugninja.schemas.models import FileUploadInfo
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


def get_test_case_analyzer_user_prompt(
    file_contents: Dict[str, str], project_description: str, extra: str = ""
) -> str:
    """Generate user prompt for test case analyzer agent.

    Args:
        file_contents (Dict[str, str]): Dictionary mapping file paths to their contents
        project_description (str): Project description from PROJECT_DESC.md
        extra (str): Extra instructions for customization

    Returns:
        str: Formatted user prompt for test case analysis

    Example:
        ```python
        prompt = get_test_case_analyzer_user_prompt(
            {"test.py": "def test_login(): pass"},
            "E-commerce website testing",
            "Focus on mobile testing"
        )
        ```
    """
    # Format file contents for analysis
    formatted_contents = []
    for file_path, content in file_contents.items():
        formatted_contents.append(f"**File: {file_path}**\n```\n{content}\n```")

    formatted_file_contents = "\n\n".join(formatted_contents)

    return __parsed_prompt(
        "test_case_analyzer_user_prompt.md",
        {
            "PROJECT_DESCRIPTION": project_description,
            "FILE_CONTENTS": formatted_file_contents,
            "EXTRA": extra if extra else "No specific requirements",
        },
    )


def get_test_case_creator_user_prompt(
    test_scenario: str, file_contents: Dict[str, str], project_description: str, extra: str = ""
) -> str:
    """Generate user prompt for test case creator agent.

    Args:
        test_scenario (str): The test scenario to generate a test case for
        file_contents (Dict[str, str]): Dictionary mapping file paths to their contents
        project_description (str): Project description from PROJECT_DESC.md
        extra (str): Extra instructions for customization

    Returns:
        str: Formatted user prompt for test case creation

    Example:
        ```python
        prompt = get_test_case_creator_user_prompt(
            "User login flow",
            {"login.py": "def login(): pass"},
            "E-commerce website testing",
            "Focus on mobile testing"
        )
        ```
    """
    # Format file contents for analysis
    formatted_contents = []
    for file_path, content in file_contents.items():
        formatted_contents.append(f"**File: {file_path}**\n```\n{content}\n```")

    formatted_file_contents = "\n\n".join(formatted_contents)

    return __parsed_prompt(
        "test_case_creator_user_prompt.md",
        {
            "TEST_SCENARIO": test_scenario,
            "FILE_CONTENTS": formatted_file_contents,
            "PROJECT_DESCRIPTION": project_description,
            "EXTRA": extra if extra else "No specific requirements",
        },
    )


def get_test_case_generator_user_prompt(
    project_description: str, n: int, p_ratio: float, extra: str = ""
) -> str:
    """Generate user prompt for test case generator agent.

    Args:
        project_description (str): Project description from PROJECT_DESC.md
        n (int): Number of test cases to generate
        p_ratio (float): Positive test case ratio (0.0-1.0)
        extra (str): Extra instructions for customization

    Returns:
        str: Formatted user prompt for test case generation

    Example:
        ```python
        prompt = get_test_case_generator_user_prompt(
            "E-commerce website",
            5,
            0.75,
            "Focus on payment flows"
        )
        ```
    """
    import math

    # Calculate positive and negative test case counts
    positive_count = math.ceil(n * p_ratio)
    negative_count = n - positive_count

    # Format the ratio information
    p_ratio_percent = int(p_ratio * 100)
    n_ratio_percent = 100 - p_ratio_percent

    ratio_info = f"{p_ratio_percent}% of test cases must be positive paths, and {n_ratio_percent}% must be negative, which for the {n} test cases should be {positive_count} positive and {negative_count} negative test"

    return __parsed_prompt(
        "test_case_generator_user_prompt.md",
        {
            "PROJECT_DESCRIPTION": project_description,
            "N": str(n),
            "TEST_DISTRIBUTION_INFO": ratio_info,
            "EXTRA": extra if extra else "No specific requirements",
        },
    )


def get_io_extraction_prompt(output_schema: Dict[str, str]) -> str:
    """Generate I/O extraction prompt from output schema.

    Args:
        output_schema (Dict[str, str]): Dictionary mapping variable names to descriptions

    Returns:
        str: Formatted prompt with extraction instructions, or empty string if no outputs

    Example:
        ```python
        prompt = get_io_extraction_prompt({
            "USER_ID": "ID of the newly registered user",
            "CONFIRMATION_CODE": "Email confirmation code"
        })
        ```
    """
    if not output_schema:
        return ""

    # Format expected outputs as a list
    outputs_list = "\n".join(
        [f"- **{key}**: {description}" for key, description in output_schema.items()]
    )

    return __parsed_prompt("io_extraction_prompt.md", {"EXPECTED_OUTPUTS_LIST": outputs_list})


def get_data_extraction_prompt(brain_states_text: str, expected_outputs_text: str) -> str:
    """Generate data extraction prompt from brain states and output schema.

    Args:
        brain_states_text (str): Formatted brain states text
        expected_outputs_text (str): Formatted expected outputs text

    Returns:
        str: Formatted prompt for data extraction

    Example:
        ```python
        prompt = get_data_extraction_prompt(
            brain_states_text="Brain State 1: Memory: ...",
            expected_outputs_text="- USER_ID: ID of the user"
        )
        ```
    """
    return __parsed_prompt(
        "data_extraction_prompt.md",
        {
            "EXPECTED_OUTPUTS_LIST": expected_outputs_text,
            "BRAIN_STATES_TEXT": brain_states_text,
        },
    )


def get_input_schema_prompt(input_schema: Dict[str, str], input_values: Dict[str, Any]) -> str:
    """Generate input schema prompt with descriptions and values from dependent tasks.

    Args:
        input_schema (Dict[str, str]): Dictionary mapping input keys to their descriptions
        input_values (Dict[str, Any]): Dictionary mapping input keys to their actual values

    Returns:
        str: Formatted prompt with input schema information, or empty string if no input schema

    Example:
        ```python
        prompt = get_input_schema_prompt(
            {"USER_ID": "ID of the user", "TOKEN": "Authentication token"},
            {"USER_ID": "12345", "TOKEN": "abc123"}
        )
        ```
    """
    if not input_schema or not input_values:
        return ""

    # Create structured input information with descriptions and values
    input_info_items = []
    for key in input_schema.keys():
        description = input_schema.get(key, "No description available")
        value = input_values.get(key, "Value not provided")

        input_info_items.append(f"- **{key}**")
        input_info_items.append(f"  - **Description**: {description}")
        input_info_items.append(f"  - **Value**: `{value}`")
        input_info_items.append("")  # Empty line for spacing

    # Join all items and remove the last empty line
    input_schema_info = "\n".join(input_info_items).rstrip()

    return __parsed_prompt(
        "input_schema_prompt.md",
        {"INPUT_SCHEMA_INFO": input_schema_info},
    )


def get_available_files_prompt(available_files: List[FileUploadInfo]) -> str:
    """Generate available files prompt from file list.

    This function creates a formatted prompt that informs the AI agent about
    files available for upload during task execution, including file indices,
    names, extensions, and descriptions.

    Args:
        available_files (List[FileUploadInfo]): List of available files for upload

    Returns:
        str: Formatted prompt with file information, or empty string if no files

    Example:
        ```python
        from bugninja.prompts.prompt_factory import get_available_files_prompt
        from bugninja.schemas.models import FileUploadInfo
        from pathlib import Path

        files = [
            FileUploadInfo(
                index=0,
                name="Resume",
                path=Path("./resume.pdf"),
                extension="pdf",
                description="Sample resume for testing"
            )
        ]

        prompt = get_available_files_prompt(files)
        ```
    """
    if not available_files:
        return ""

    # Format file list
    file_items = []
    for file_info in available_files:
        file_items.append(f"**File Index {file_info.index}**: {file_info.name}")
        file_items.append(f"  - Extension: .{file_info.extension}")
        file_items.append(f"  - Description: {file_info.description}")
        file_items.append("")

    file_list_text = "\n".join(file_items).rstrip()

    return __parsed_prompt("file_upload_prompt.md", {"FILE_LIST": file_list_text})


BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="navigator_agent_system_prompt.md"
)

HEALDER_AGENT_EXTRA_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="healer_agent_extra_sytem_prompt.md"
)

TEST_CASE_ANALYZER_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="test_case_analyzer_system_prompt.md"
)

TEST_CASE_CREATOR_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="test_case_creator_system_prompt.md"
)

TEST_CASE_GENERATOR_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="test_case_generator_system_prompt.md"
)
