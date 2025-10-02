"""
Test case analyzer agent for Bugninja.

This module provides the **TestCaseAnalyzerAgent** for analyzing imported files
and determining their suitability for Bugninja test case generation.
"""

import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from bugninja.config import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)
from bugninja.prompts.prompt_factory import (
    TEST_CASE_ANALYZER_SYSTEM_PROMPT,
    get_test_case_analyzer_user_prompt,
)
from bugninja.schemas.test_case_import import TestCaseImportAnalysisOutput
from bugninja.utils.logging_config import logger


class TestCaseAnalyzerAgent:
    """AI agent for analyzing imported files and determining test case generation capability.

    This agent analyzes various file types (Excel, CSV, DocX, PDF, Gherkin, Python,
    TypeScript, JavaScript, TOML) to determine if they contain sufficient information
    for generating Bugninja browser automation test cases.

    Attributes:
        llm (BaseChatModel): Language model for analysis
        system_prompt (str): System prompt for the agent

    ### Key Methods

    1. **analyze_files_for_test_cases()** -> `TestCaseImportAnalysisOutput`: - Analyze files for test case capability
    2. **format_file_contents()** -> `str`: - Format file contents for analysis
    3. **parse_analysis_output()** -> `TestCaseImportAnalysisOutput`: - Parse LLM response into structured output

    Example:
        ```python
        from bugninja.agents.test_case_analyzer import TestCaseAnalyzerAgent
        from bugninja.config import create_llm_model_from_config

        # Create agent with LLM
        llm = create_llm_model_from_config(llm_config)
        agent = TestCaseAnalyzerAgent(llm, system_prompt)

        # Analyze files for test case capability
        analysis = await agent.analyze_files_for_test_cases(
            file_contents={"test.py": "def test_login(): pass"},
            project_description="E-commerce website testing"
        )

        if analysis.test_case_capable:
            print(f"Found {analysis.number_of_potential_testcases} potential test cases")
        else:
            print("Files not suitable for test case generation")
        ```
    """

    def __init__(self, cli_mode: bool = False):
        """Initialize the test case analyzer agent.

        Args:
            cli_mode (bool): Whether running in CLI mode
        """

        llm_config = create_llm_config_from_settings(cli_mode=cli_mode)
        self.llm = create_llm_model_from_config(llm_config, cli_mode=cli_mode)

        self.system_prompt = TEST_CASE_ANALYZER_SYSTEM_PROMPT

    async def analyze_files_for_test_cases(
        self, file_contents: Dict[str, str], project_description: str, extra: str = ""
    ) -> TestCaseImportAnalysisOutput:
        """Analyze imported files to determine test case generation capability.

        This method uses AI to analyze the provided files and determine whether
        they contain sufficient information for generating Bugninja test cases.

        Args:
            file_contents (Dict[str, str]): Dictionary mapping file paths to their contents
            project_description (str): Project description from PROJECT_DESC.md
            extra (str): Extra instructions for customization

        Returns:
            TestCaseImportAnalysisOutput: Analysis results including capability assessment

        Raises:
            ValueError: If analysis fails or output cannot be parsed
            RuntimeError: If LLM response is invalid or incomplete
        """
        try:
            # Create messages for LLM
            system_message = SystemMessage(content=self.system_prompt)
            user_prompt = get_test_case_analyzer_user_prompt(
                file_contents, project_description, extra
            )
            user_message = HumanMessage(content=user_prompt)

            # Call LLM with JSON mode for structured output
            response = await self.llm.ainvoke([system_message, user_message])

            # Parse the response into structured output
            # Handle different response content types
            content = response.content
            if isinstance(content, list):
                # Extract text from list of content blocks
                content = "".join([str(item) for item in content if isinstance(item, str)])
            elif not isinstance(content, str):
                content = str(content)

            analysis_output = self._parse_analysis_output(content)

            logger.info(
                f"File analysis completed. Test case capable: {analysis_output.test_case_capable}"
            )
            return analysis_output

        except Exception as e:
            logger.error(f"Failed to analyze files for test cases: {e}")
            raise RuntimeError(f"Analysis failed: {e}")

    def _parse_analysis_output(self, llm_response: str) -> TestCaseImportAnalysisOutput:
        """Parse LLM response into structured output.

        Args:
            llm_response (str): Raw LLM response

        Returns:
            TestCaseImportAnalysisOutput: Parsed analysis results

        Raises:
            ValueError: If response cannot be parsed as valid JSON
            KeyError: If required fields are missing from response
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in LLM response")

            json_str = llm_response[json_start:json_end]
            analysis_data = json.loads(json_str)

            # Validate required fields
            required_fields = [
                "file_descriptions",
                "import_reasoning",
                "test_case_capable",
                "testing_scenarios",
                "test_data",
                "number_of_potential_testcases",
                "test_dependencies",
            ]

            for field in required_fields:
                if field not in analysis_data:
                    raise KeyError(f"Missing required field: {field}")

            return TestCaseImportAnalysisOutput(**analysis_data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse analysis output: {e}")
