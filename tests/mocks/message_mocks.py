from unittest.mock import MagicMock


class MockMessageManager:
    """Mock message manager for testing"""

    def __init__(self):
        self.messages = []
        self.settings = MagicMock()
        self.settings.message_context = ""
        self.state = MagicMock()
        self.state.history = MagicMock()
        self.state.history.current_tokens = 0

        self.add_state_message = MagicMock()
        self.add_model_output = MagicMock()
        self.add_plan = MagicMock()
        self._add_message_with_tokens = MagicMock()
        self._remove_last_state_message = MagicMock()
        self.get_messages = MagicMock(return_value=[])
