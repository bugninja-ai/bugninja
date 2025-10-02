"""
Test case generator agent for Bugninja.

This module provides the **TestCaseGeneratorAgent** for generating test cases
from scratch using project descriptions and user requirements.
"""

import json
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from bugninja.config import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)
from bugninja.prompts.prompt_factory import (
    TEST_CASE_GENERATOR_SYSTEM_PROMPT,
    get_test_case_generator_user_prompt,
)
from bugninja.schemas.test_case_creation import TestCaseCreationOutput
from bugninja.utils.logging_config import logger


class TestCaseGeneratorAgent:
    """AI agent for generating test cases from project descriptions.

    This agent generates test cases from scratch using project descriptions,
    with emphasis on both positive and negative test paths. It creates
    independent test cases suitable for browser automation.

    Attributes:
        llm (BaseChatModel): Language model for generation
        system_prompt (str): System prompt for the agent

    ### Key Methods

    1. **generate_test_cases()** -> `List[TestCaseCreationOutput]`: - Generate multiple test cases
    2. **generate_single_test_case()** -> `TestCaseCreationOutput`: - Generate one test case
    3. **parse_generation_output()** -> `TestCaseCreationOutput`: - Parse LLM response into structured output

    Example:
        ```python
        from bugninja.agents.test_case_generator import TestCaseGeneratorAgent

        # Create agent
        agent = TestCaseGeneratorAgent(cli_mode=True)

        # Generate test cases
        test_cases = await agent.generate_test_cases(
            project_description="E-commerce website",
            n=5,
            extra="Focus on payment flows"
        )

        for test_case in test_cases:
            print(f"Generated: {test_case.task_name}")
        ```
    """

    def __init__(self, cli_mode: bool = False):
        """Initialize the test case generator agent.

        Args:
            cli_mode (bool): Whether running in CLI mode
        """
        llm_config = create_llm_config_from_settings(cli_mode=cli_mode)
        self.llm = create_llm_model_from_config(llm_config, cli_mode=cli_mode)

        self.system_prompt = TEST_CASE_GENERATOR_SYSTEM_PROMPT

    async def generate_test_cases(
        self,
        project_description: str,
        n: int,
        p_ratio: float,
        extra: str = "",
    ) -> List[TestCaseCreationOutput]:
        """Generate multiple test cases from project description.

        This method generates n test cases with a customizable positive/negative
        test path ratio, ensuring all test cases are independent.

        Args:
            project_description (str): Project description from PROJECT_DESC.md
            n (int): Number of test cases to generate
            p_ratio (float): Positive test case ratio (0.0-1.0)
            extra (str): Extra instructions for customization

        Returns:
            List[TestCaseCreationOutput]: List of generated test cases

        Raises:
            ValueError: If generation fails or output cannot be parsed
            RuntimeError: If LLM response is invalid or incomplete
        """
        try:
            # Create messages for LLM
            system_message = SystemMessage(content=self.system_prompt)
            user_prompt = get_test_case_generator_user_prompt(
                project_description, n, p_ratio, extra
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

            generation_output = self._parse_generation_output(content)

            logger.info(f"Generated {len(generation_output)} test cases")
            return generation_output

        except Exception as e:
            logger.error(f"Failed to generate test cases: {e}")
            raise RuntimeError(f"Test case generation failed: {e}")

    def _parse_generation_output(self, llm_response: str) -> List[TestCaseCreationOutput]:
        """Parse LLM response into structured output.

        Args:
            llm_response (str): Raw LLM response

        Returns:
            List[TestCaseCreationOutput]: Parsed test case generation results

        Raises:
            ValueError: If response cannot be parsed as valid JSON
            KeyError: If required fields are missing from response
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = llm_response.find("[")
            json_end = llm_response.rfind("]") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON array found in LLM response")

            json_str = llm_response[json_start:json_end]
            generation_data = json.loads(json_str)

            # Validate that we have a list of test cases
            if not isinstance(generation_data, list):
                raise ValueError("Expected JSON array of test cases")

            # Parse each test case
            test_cases = []
            for i, test_case_data in enumerate(generation_data):
                try:
                    # Validate required fields
                    required_fields = [
                        "task_name",
                        "description",
                        "extra_instructions",
                        "secrets",
                    ]

                    for field in required_fields:
                        if field not in test_case_data:
                            raise KeyError(f"Missing required field: {field} in test case {i}")

                    test_case = TestCaseCreationOutput(**test_case_data)
                    test_cases.append(test_case)
                except Exception as e:
                    logger.warning(f"Failed to parse test case {i}: {e}")
                    continue

            if not test_cases:
                raise ValueError("No valid test cases found in response")

            return test_cases

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse generation output: {e}")
