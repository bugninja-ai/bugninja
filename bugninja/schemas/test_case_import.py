"""
Test case import analysis schemas for Bugninja.

This module provides Pydantic models for analyzing imported files
and determining their suitability for Bugninja test case generation.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class TestScenario(BaseModel):
    """Individual test scenario with dependencies and metadata.

    This model represents a single test scenario that can be generated
    from the imported files, including its dependencies and relationships.

    Attributes:
        idx (int): Index of this test scenario in the list
        test_scenario (str): Description of the test case
        file_dependencies (List[str]): List of file paths this test case depends on
    """

    idx: int = Field(description="Index of this test scenario in the list")
    test_scenario: str = Field(description="Description of the test case")
    file_dependencies: List[str] = Field(description="List of file paths this test case depends on")


class TestCaseImportAnalysisOutput(BaseModel):
    """Analysis output for determining test case generation capability from imported files.

    This model represents the AI agent's analysis of imported files to determine
    whether they contain sufficient information for generating Bugninja test cases.

    Attributes:
        import_reasoning (str): Overall analysis of the provided files with structured reasoning
        file_descriptions (List[str]): List of file descriptions with their role/content and relationships
        testing_scenarios (List[TestScenario]): List of test scenarios with dependencies and metadata
        test_data (str): Free language description of test data provided in the files
        test_case_capable (bool): Whether the files are suitable for Bugninja test case generation
        number_of_potential_testcases (int): Number of potential test cases that could be generated
        test_dependencies (Dict[int, List[int]]): Dependencies between test cases (testcase_idx -> list of dependent testcase indices)
    """

    import_reasoning: str = Field(
        description="Overall analysis of the provided files with structured reasoning including file descriptions, testing scenarios, and test data analysis"
    )
    file_descriptions: List[str] = Field(
        description="List of file descriptions with 1-2 sentences about their role/content and relationships to other files"
    )
    test_case_capable: bool = Field(
        description="Whether the files are suitable for Bugninja test case generation"
    )
    testing_scenarios: List[TestScenario] = Field(
        description="List of test scenarios with their dependencies and metadata"
    )
    test_data: str = Field(
        description="Free language description of what kind of test data is provided inside the files"
    )

    number_of_potential_testcases: int = Field(
        description="Number of potential test cases that could be generated using the files as context"
    )
    test_dependencies: Dict[int, List[int]] = Field(
        description="Dependencies between test cases (testcase_idx -> list of dependent testcase indices). Must avoid circular dependencies."
    )
