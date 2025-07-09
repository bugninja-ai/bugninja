from typing import List
from unittest.mock import AsyncMock

from browser_use.agent.views import AgentOutput


class MockLLMModel:
    """Mock LLM model for testing"""

    def __init__(self, responses: List[AgentOutput] = None):
        self.responses = responses or []
        self.response_index = 0
        self.invoke = AsyncMock(side_effect=self._get_response)

    def _get_response(self, *args, **kwargs):
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return AgentOutput(action=[])


class MockPageExtractionLLM:
    """Mock page extraction LLM"""

    def __init__(self):
        self.invoke = AsyncMock(return_value="Extracted content")


class MockPlannerLLM:
    """Mock planner LLM"""

    def __init__(self):
        self.invoke = AsyncMock(return_value="Test plan")
