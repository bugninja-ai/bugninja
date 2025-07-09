from unittest.mock import AsyncMock, MagicMock

from browser_use.agent.views import ActionResult


class MockController:
    """Mock controller for testing"""

    def __init__(self):
        self.registry = MagicMock()
        self.act = AsyncMock(return_value=ActionResult(extracted_content="Action completed"))

    def get_prompt_description(self, page=None):
        return "Available actions: click, fill, goto"


class MockBugninjaController(MockController):
    """Mock Bugninja-specific controller"""

    def __init__(self):
        super().__init__()
        # Add Bugninja-specific methods
        self.extend_action = AsyncMock()
