from typing import List, Optional
from unittest.mock import MagicMock

from browser_use.agent.views import AgentBrain
from browser_use.controller.registry.views import ActionModel

from tests.mocks.browser_mocks import MockBrowserSession


class MockAgentOutput:
    """Mock agent output for testing"""

    def __init__(
        self,
        actions: Optional[List[ActionModel]] = None,
        current_state: Optional[AgentBrain] = None,
    ):
        self.action = actions or []
        self.current_state = current_state or AgentBrain(thought="Test thought")


class MockActionResult:
    """Mock action result for testing"""

    def __init__(
        self, success: bool = True, error: Optional[str] = None, extracted_content: str = ""
    ):
        self.success = success
        self.error = error
        self.extracted_content = extracted_content
        self.is_done = False


class MockBugninjaAgentBase:
    """Mock base agent for testing concrete implementations"""

    def __init__(self):
        self.state = MagicMock()
        self.state.n_steps = 0
        self.state.last_result = []
        self.state.consecutive_failures = 0

        self.settings = MagicMock()
        self.settings.use_vision = False
        self.settings.planner_interval = 5
        self.settings.save_conversation_path = None

        self.browser_session = MockBrowserSession()
        self.controller = MagicMock()
        self._message_manager = MagicMock()
        self.memory = MagicMock()
        self.enable_memory = False
