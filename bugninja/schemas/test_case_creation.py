"""
Test case creation schemas for Bugninja.

This module provides Pydantic models for generating Bugninja test cases
from imported files and AI analysis results.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class TestCaseCreationOutput(BaseModel):
    """Output model for test case creation from imported files.

    This model represents the AI agent's generated test case content
    that will be converted into a Bugninja-compatible TOML file.

    Attributes:
        task_name (str): Name of the test case (extracted from context or AI-generated)
        description (str): Description of what the test case does
        extra_instructions (List[str]): List of step-by-step instructions for the test
        secrets (Dict[str, str]): Test data/secrets found in context (empty if none found)
    """

    task_name: str = Field(
        description="Name of the test case - extract from context if available, otherwise generate based on content"
    )
    description: str = Field(
        description="Clear description of what the test case does and its purpose"
    )
    extra_instructions: List[str] = Field(
        description="List of step-by-step instructions for executing the test case"
    )
    secrets: Dict[str, str] = Field(
        default_factory=dict,
        description="Test data/secrets found in context - only include if actually found in files, otherwise leave empty",
    )
