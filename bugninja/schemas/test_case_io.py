"""
Test case I/O schema definitions for Bugninja.

This module provides Pydantic models for defining input and output schemas
for test cases, enabling data extraction and validation capabilities.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TestCaseSchema(BaseModel):
    """Unified schema for test case input and output definitions.

    This model combines both input and output schema functionality
    into a single, more maintainable structure.

    Attributes:
        input_schema (Optional[Dict[str, Any]]): Input data schema for validation
        output_schema (Optional[Dict[str, str]]): Output extraction schema
    """

    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Input data schema defining expected structure and types"
    )

    output_schema: Optional[Dict[str, str]] = Field(
        default=None,
        description="Output extraction schema - Dict[str, str] where keys are variable names and values are descriptions",
    )

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Validate that output_schema is Dict[str, str] format.

        Args:
            v (Optional[Dict[str, str]]): The schema dictionary to validate

        Returns:
            Optional[Dict[str, str]]: The validated schema dictionary

        Raises:
            ValueError: If schema is not in Dict[str, str] format
        """
        if v is None:
            return v
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("output_schema must be Dict[str, str] format")
        return v
