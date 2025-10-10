"""
Data extraction agent for Bugninja.

This module provides the **DataExtractionAgent** for extracting structured data
from brain states and actions based on expected output schemas.
"""

import json
from typing import Any, Dict

from browser_use.agent.views import AgentBrain  # type: ignore
from langchain_core.messages import HumanMessage

from bugninja.config import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)
from bugninja.prompts.prompt_factory import get_data_extraction_prompt
from bugninja.utils.logging_config import logger


class DataExtractionAgent:
    """AI agent for extracting structured data from brain states and actions.

    This agent analyzes brain states from browser automation sessions and extracts
    specific information based on expected output schemas. It uses LLM capabilities
    to understand the context and extract the requested data.

    Attributes:
        llm (BaseChatModel): Language model for data extraction
        cli_mode (bool): Whether running in CLI mode

    Example:
        ```python
        from bugninja.agents.data_extraction_agent import DataExtractionAgent

        # Create extraction agent
        agent = DataExtractionAgent(cli_mode=True)

        # Extract data from brain states
        extracted_data = await agent.extract_data_from_brain_states(
            brain_states=brain_states,
            output_schema={"USER_ID": "ID of the registered user"}
        )

        print(f"Extracted: {extracted_data}")
        ```
    """

    def __init__(self, cli_mode: bool = False):
        """Initialize the data extraction agent.

        Args:
            cli_mode (bool): Whether running in CLI mode
        """
        self.llm = create_llm_model_from_config(create_llm_config_from_settings())
        self.cli_mode = cli_mode

    async def extract_data_from_brain_states(
        self, brain_states: Dict[str, AgentBrain], output_schema: Dict[str, str]
    ) -> Dict[str, Any]:
        """Extract structured data from brain states based on output schema.

        Args:
            brain_states (Dict[str, AgentBrain]): Brain states from the automation session
            output_schema (Dict[str, str]): Schema defining what to extract

        Returns:
            Dict[str, Any]: Extracted data with keys from output_schema

        Example:
            ```python
            extracted = await agent.extract_data_from_brain_states(
                brain_states={"state_1": brain_state},
                output_schema={"USER_ID": "ID of the user"}
            )
            # Returns: {"USER_ID": "user_12345"}
            ```
        """
        if not output_schema:
            return {}

        # Create extraction prompt
        extraction_prompt = self._create_extraction_prompt(brain_states, output_schema)

        try:
            # Get LLM response
            response = await self.llm.ainvoke([HumanMessage(content=extraction_prompt)])

            # Parse and validate extracted data
            # Handle both string and list response types
            content = response.content
            if isinstance(content, list):
                # If content is a list, join all string elements
                content = " ".join(str(item) for item in content if isinstance(item, str))
            elif not isinstance(content, str):
                # If content is not a string, convert to string
                content = str(content)

            extracted_data = self._parse_extraction_response(content, output_schema)

            logger.bugninja_log(f"📊 Data extraction completed: {extracted_data}")
            return extracted_data

        except Exception as e:
            logger.warning(f"Data extraction failed: {e}")
            # Return empty dict with null values if extraction fails
            return {key: None for key in output_schema.keys()}

    def _create_extraction_prompt(
        self, brain_states: Dict[str, AgentBrain], output_schema: Dict[str, str]
    ) -> str:
        """Create prompt for data extraction from brain states.

        Args:
            brain_states (Dict[str, AgentBrain]): Brain states to analyze
            output_schema (Dict[str, str]): Schema defining what to extract

        Returns:
            str: Formatted extraction prompt
        """

        brain_states_text = "\n\n".join(
            [
                f"Brain State {state_id}:\n"
                f"Memory: {state.memory}\n"
                f"Next Goal: {state.next_goal}\n"
                f"Evaluation: {state.evaluation_previous_goal}"
                for state_id, state in brain_states.items()
            ]
        )

        expected_outputs_text = "\n".join(
            [f"- {key}: {description}" for key, description in output_schema.items()]
        )

        return get_data_extraction_prompt(brain_states_text, expected_outputs_text)

    def _parse_extraction_response(
        self, response: str, output_schema: Dict[str, str]
    ) -> Dict[str, Any]:
        """Parse and validate the extraction response.

        Args:
            response (str): Raw LLM response
            output_schema (Dict[str, str]): Expected output schema

        Returns:
            Dict[str, Any]: Parsed and validated extracted data
        """
        try:
            # Clean the response (remove any non-JSON text)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Remove any text before/after JSON if present
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                response = response[start:end]

            extracted_data = json.loads(response)

            # Validate that all expected keys are present and filter out any extra keys
            result = {}
            for key in output_schema.keys():
                if key in extracted_data:
                    result[key] = extracted_data[key]
                else:
                    result[key] = None

            # Log warning if extra keys were found
            extra_keys = set(extracted_data.keys()) - set(output_schema.keys())
            if extra_keys:
                logger.warning(f"Extra keys found in extraction response (ignored): {extra_keys}")

            return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            # Return empty dict with null values if parsing fails
            return {key: None for key in output_schema.keys()}
