"""
Markdown parser for Bugninja task files.

This module provides functionality to parse markdown task files and extract
task configuration including description, secrets, and other parameters.
"""

import re
from pathlib import Path
from typing import Any, Dict

# TODO!:AGENT have to rethink


def parse_task_markdown(file_path: Path) -> Dict[str, Any]:
    """Parse markdown file and extract task configuration.

    This function parses a markdown task file and extracts all configuration
    parameters including description, allowed domains, max steps, target URL,
    and secrets. It supports environment variable substitution in the secrets
    section using `{{VARIABLE_NAME}}` syntax.

    The function expects a specific markdown structure with sections:
    - `## Description`: Required task description
    - `## Configuration`: Optional configuration settings
    - `## Secrets`: Optional JSON secrets with environment variable support

    Args:
        file_path: Path to the markdown task file to parse

    Returns:
        Dictionary containing parsed task configuration with keys:
        - description: Task description string
        - allowed_domains: List of allowed domain strings
        - max_steps: Maximum steps integer (default: 100)
        - secrets: Dictionary of secrets with environment variables resolved

    Raises:
        ValueError: If required fields are missing, invalid, or malformed
        FileNotFoundError: If the task file does not exist
        json.JSONDecodeError: If the secrets JSON is invalid
    """

    if not file_path.exists():
        raise ValueError(f"Task file does not exist: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract task description (everything after ## Description until next ##)
    # This regex captures all content between ## Description and the next ## or end of file
    description_match = re.search(r"## Description\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if not description_match:
        raise ValueError("Task file must contain a '## Description' section")

    description = description_match.group(1).strip()
    if not description:
        raise ValueError("Task description cannot be empty")

    # Initialize config with defaults
    config: Dict[str, Any] = {
        "description": description,
        "secrets": {},
        "allowed_domains": [],
        "max_steps": 100,
    }

    # Extract configuration from ## Configuration section
    # This section contains optional configuration parameters like domains, steps, and URLs
    config_match = re.search(r"## Configuration\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if config_match:
        config_section = config_match.group(1)

        # Parse allowed domains (comma-separated list)
        domains_match = re.search(r"Allowed Domains[:\s]*([^\n]+)", config_section, re.IGNORECASE)
        if domains_match:
            domains_str = domains_match.group(1).strip()
            config["allowed_domains"] = [d.strip() for d in domains_str.split(",") if d.strip()]

        # Parse max steps (must be a positive integer)
        steps_match = re.search(r"Max Steps[:\s]*(\d+)", config_section, re.IGNORECASE)
        if steps_match:
            config["max_steps"] = int(steps_match.group(1))

    return config


def validate_task_config(config: Dict[str, Any]) -> None:
    """Validate parsed task configuration.

    This function performs comprehensive validation of the parsed task
    configuration to ensure all required fields are present and valid.
    It checks for required fields, validates numeric ranges, and ensures
    data types are correct.

    Args:
        config: Task configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid with specific error details:
        - Task description is missing or empty
        - Max steps is not positive or exceeds limit (1000)
        - Secrets is not a dictionary
    """
    if not config.get("description"):
        raise ValueError("Task description is required")

    if config.get("max_steps", 0) <= 0:
        raise ValueError("Max steps must be greater than 0")

    if config.get("max_steps", 0) > 1000:
        raise ValueError("Max steps cannot exceed 1000")

    # Validate secrets if present
    secrets = config.get("secrets", {})
    if not isinstance(secrets, dict):
        raise ValueError("Secrets must be a dictionary")
