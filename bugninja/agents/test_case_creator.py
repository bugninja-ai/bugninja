"""
Test case creator agent for Bugninja.

This module provides the **TestCaseCreatorAgent** for generating actual
Bugninja test cases from imported files and analysis results.
"""

import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from bugninja.config import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)
from bugninja.prompts.prompt_factory import (
    TEST_CASE_CREATOR_SYSTEM_PROMPT,
    get_test_case_creator_user_prompt,
)
from bugninja.schemas.test_case_creation import TestCaseCreationOutput
from bugninja.schemas.test_case_import import TestScenario
from bugninja.utils.logging_config import logger


class TestCaseCreatorAgent:
    """AI agent for generating Bugninja test cases from analysis results.

    This agent takes the first test scenario from file analysis and generates
    a complete, executable Bugninja test case that can be saved as a TOML file.

    Attributes:
        llm (BaseChatModel): Language model for test case generation
        system_prompt (str): System prompt for the agent

    ### Key Methods

    1. **generate_test_case()** -> `TestCaseCreationOutput`: - Generate test case from scenario
    2. **format_file_contents()** -> `str`: - Format file contents for generation
    3. **parse_creation_output()** -> `TestCaseCreationOutput`: - Parse LLM response into structured output

    Example:
        ```python
        from bugninja.agents.test_case_creator import TestCaseCreatorAgent
        from bugninja.schemas.test_case_import import TestScenario

        # Create agent with LLM
        agent = TestCaseCreatorAgent(cli_mode=True)

        # Generate test case from scenario
        scenario = TestScenario(
            idx=0,
            test_scenario="User login flow",
            file_dependencies=["login.py", "users.csv"]
        )

        result = await agent.generate_test_case(
            scenario=scenario,
            file_contents={"login.py": "def login(): pass"},
            project_description="E-commerce website testing"
        )

        print(f"Generated test case: {result.task_name}")
        ```
    """

    def __init__(self, cli_mode: bool = False):
        """Initialize the test case creator agent.

        Args:
            cli_mode (bool): Whether running in CLI mode
        """
        llm_config = create_llm_config_from_settings(cli_mode=cli_mode)
        self.llm = create_llm_model_from_config(llm_config, cli_mode=cli_mode)

        self.system_prompt = TEST_CASE_CREATOR_SYSTEM_PROMPT

    async def generate_test_case(
        self,
        scenario: TestScenario,
        file_contents: Dict[str, str],
        project_description: str,
        extra: str = "",
    ) -> TestCaseCreationOutput:
        """Generate a Bugninja test case from a test scenario.

        This method uses AI to generate a complete test case including task name,
        description, instructions, and secrets based on the provided scenario
        and file context.

        Args:
            scenario (TestScenario): The test scenario to generate a test case for
            file_contents (Dict[str, str]): Dictionary mapping file paths to their contents
            project_description (str): Project description from PROJECT_DESC.md
            extra (str): Extra instructions for customization

        Returns:
            TestCaseCreationOutput: Generated test case content

        Raises:
            ValueError: If generation fails or output cannot be parsed
            RuntimeError: If LLM response is invalid or incomplete
        """
        try:
            # Create messages for LLM
            system_message = SystemMessage(content=self.system_prompt)
            user_prompt = get_test_case_creator_user_prompt(
                scenario.test_scenario, file_contents, project_description, extra
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

            creation_output = self._parse_creation_output(content)

            logger.info(f"Test case generation completed. Task name: {creation_output.task_name}")
            return creation_output

        except Exception as e:
            logger.error(f"Failed to generate test case: {e}")
            raise RuntimeError(f"Test case generation failed: {e}")

    def _parse_creation_output(self, llm_response: str) -> TestCaseCreationOutput:
        """Parse LLM response into structured output.

        Args:
            llm_response (str): Raw LLM response

        Returns:
            TestCaseCreationOutput: Parsed test case creation results

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
            creation_data = json.loads(json_str)

            # Validate required fields
            required_fields = [
                "task_name",
                "description",
                "extra_instructions",
                "secrets",
            ]

            for field in required_fields:
                if field not in creation_data:
                    raise KeyError(f"Missing required field: {field}")

            return TestCaseCreationOutput(**creation_data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse creation output: {e}")
