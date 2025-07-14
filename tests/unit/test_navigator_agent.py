import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from browser_use.agent.views import AgentBrain, AgentOutput
from browser_use.browser.session import Page
from browser_use.browser.views import BrowserStateSummary
from browser_use.controller.registry.views import ActionModel
from cuid2 import Cuid as CUID

from src.agents.extensions import BugninjaController
from src.agents.navigator_agent import NavigatorAgent
from src.schemas.pipeline import BugninjaBrowserConfig, BugninjaExtendedAction, Traversal


class TestNavigatorAgent:
    """Test suite for NavigatorAgent class"""

    @pytest.fixture
    def navigator_agent(self) -> None:
        """Create a NavigatorAgent instance for testing"""
        agent = NavigatorAgent()

        # Initialize required attributes from parent class
        agent.state = MagicMock()
        agent.state.n_steps = 0
        agent.state.last_result = []
        agent.state.consecutive_failures = 0

        agent.settings = MagicMock()
        agent.settings.use_vision = False
        agent.settings.planner_interval = 5
        agent.settings.save_conversation_path = None
        agent.settings.save_conversation_path_encoding = "utf-8"

        agent.browser_session = MagicMock()
        agent._message_manager = MagicMock()
        agent.memory = MagicMock()
        agent.enable_memory = False
        agent.browser_profile = MagicMock()
        agent.browser_profile.wait_between_actions = 0.1

        agent.sensitive_data = {"test_key": "test_value"}
        agent.context = {}
        agent.tool_calling_method = "raw"
        agent.task = "Test navigation task"

        # Mock action models
        agent.ActionModel = MagicMock()
        agent.DoneAgentOutput = MagicMock()

        # Mock callbacks
        agent.register_new_step_callback = None

        return agent

    @pytest.fixture
    def mock_browser_state_summary(self) -> None:
        """Create a mock browser state summary"""
        return BrowserStateSummary(
            url="https://example.com",
            title="Test Page",
            selector_map={},
            clickable_elements=[],
            form_elements=[],
            text_content="Test content",
            screenshot=None,
            accessibility_tree=None,
        )

    @pytest.fixture
    def mock_agent_output(self) -> None:
        """Create a mock agent output"""
        return AgentOutput(action=[], current_state=AgentBrain(thought="Test thought"))

    @pytest.fixture
    def mock_page(self) -> None:
        """Create a mock page"""
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
        return page

    @pytest.fixture
    def mock_action_model(self) -> None:
        """Create a mock action model"""
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None
        return action

    @pytest.fixture
    def mock_bugninja_extended_action(self) -> None:
        """Create a mock BugninjaExtendedAction"""
        return BugninjaExtendedAction(
            brain_state_id="test_brain_id",
            action_type="click",
            selectors={"css": "button", "xpath": "//button"},
            action_params={"text": "Click me"},
            element_attributes={
                "tag_name": "button",
                "attributes": {"id": "test-button"},
                "xpath": "//button[@id='test-button']",
                "css_selector": "button#test-button",
            },
            context="Testing button click",
            assertion={"type": "visible", "selector": "button"},
        )

    @pytest.fixture
    def mock_traversal_data(self) -> None:
        """Create mock traversal data"""
        return {
            "test_case": "Test navigation task",
            "browser_config": {
                "user_agent": "Test User Agent",
                "viewport": {"width": 1920, "height": 1080},
                "device_scale_factor": 1.0,
                "color_scheme": "light",
                "accept_downloads": False,
                "proxy": None,
                "client_certificates": [],
                "extra_http_headers": {},
                "http_credentials": None,
                "java_script_enabled": True,
                "geolocation": None,
                "timeout": 30000.0,
                "headers": None,
                "allowed_domains": None,
            },
            "secrets": {"test_key": "test_value"},
            "brain_states": {
                "brain_1": AgentBrain(thought="First thought"),
                "brain_2": AgentBrain(thought="Second thought"),
            },
            "actions": {
                "action_0": {
                    "brain_state_id": "brain_1",
                    "action_type": "click",
                    "selectors": {"css": "button"},
                    "action_params": {"text": "Click me"},
                    "element_attributes": {"tag_name": "button"},
                    "context": "Testing",
                    "assertion": {"type": "visible", "selector": "button"},
                }
            },
        }

    @pytest.mark.asyncio
    async def test_before_run_hook_initialization(self, navigator_agent) -> None:
        """Test that before_run_hook properly initializes agent state"""
        await navigator_agent._before_run_hook()

        # Verify agent state is initialized
        assert hasattr(navigator_agent, "agent_taken_actions")
        assert hasattr(navigator_agent, "agent_brain_states")
        assert isinstance(navigator_agent.agent_taken_actions, list)
        assert isinstance(navigator_agent.agent_brain_states, dict)
        assert len(navigator_agent.agent_taken_actions) == 0
        assert len(navigator_agent.agent_brain_states) == 0

        # Verify controller is overridden with BugninjaController
        assert isinstance(navigator_agent.controller, BugninjaController)

    @pytest.mark.asyncio
    async def test_before_run_hook_controller_override(self, navigator_agent) -> None:
        """Test that the controller is properly overridden with BugninjaController"""
        # Set a different controller first
        navigator_agent.controller = MagicMock()

        await navigator_agent._before_run_hook()

        # Verify controller was replaced with BugninjaController
        assert isinstance(navigator_agent.controller, BugninjaController)

    @pytest.mark.asyncio
    async def test_after_run_hook_calls_save_agent_actions(self, navigator_agent) -> None:
        """Test that after_run_hook calls save_agent_actions"""
        with patch.object(navigator_agent, "save_agent_actions") as mock_save:
            await navigator_agent._after_run_hook()

            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_before_step_hook_action_recording(
        self, navigator_agent, mock_browser_state_summary, mock_agent_output, mock_page
    ) -> None:
        """Test that actions are properly recorded during step execution"""
        # Initialize agent state
        await navigator_agent._before_run_hook()

        # Mock the browser session
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend_agent_action_with_info function
        mock_extended_action = MagicMock(spec=BugninjaExtendedAction)
        mock_extended_action.model_dump.return_value = {
            "brain_state_id": "test_brain_id",
            "action_type": "click",
            "selectors": {"css": "button"},
            "action_params": {"text": "Click me"},
            "element_attributes": {"tag_name": "button"},
            "context": "Testing",
            "assertion": {"type": "visible", "selector": "button"},
        }

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was recorded
            assert len(navigator_agent.agent_brain_states) == 1
            assert mock_agent_output.current_state in navigator_agent.agent_brain_states.values()

            # Verify action was recorded
            assert len(navigator_agent.agent_taken_actions) == 1
            assert navigator_agent.agent_taken_actions[0] == mock_extended_action

            # Verify extend_agent_action_with_info was called
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args
            assert call_args[1]["brain_state_id"] in navigator_agent.agent_brain_states
            assert call_args[1]["current_page"] == mock_page
            assert call_args[1]["model_output"] == mock_agent_output
            assert call_args[1]["browser_state_summary"] == mock_browser_state_summary

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_actions(
        self, navigator_agent, mock_browser_state_summary, mock_agent_output, mock_page
    ) -> None:
        """Test recording multiple actions in a single step"""
        # Initialize agent state
        await navigator_agent._before_run_hook()

        # Mock the browser session
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Create multiple mock extended actions
        mock_action1 = MagicMock(spec=BugninjaExtendedAction)
        mock_action1.model_dump.return_value = {
            "action_type": "click",
            "selectors": {"css": "button1"},
        }

        mock_action2 = MagicMock(spec=BugninjaExtendedAction)
        mock_action2.model_dump.return_value = {
            "action_type": "fill",
            "selectors": {"css": "input"},
        }

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_action1, mock_action2]

            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify both actions were recorded
            assert len(navigator_agent.agent_taken_actions) == 2
            assert navigator_agent.agent_taken_actions[0] == mock_action1
            assert navigator_agent.agent_taken_actions[1] == mock_action2

    @pytest.mark.asyncio
    async def test_before_step_hook_brain_state_generation(
        self, navigator_agent, mock_browser_state_summary, mock_agent_output, mock_page
    ) -> None:
        """Test that brain state IDs are properly generated and stored"""
        # Initialize agent state
        await navigator_agent._before_run_hook()

        # Mock the browser session
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was stored
            assert len(navigator_agent.agent_brain_states) == 1

            # Get the brain state ID that was used
            brain_state_id = list(navigator_agent.agent_brain_states.keys())[0]
            brain_state = navigator_agent.agent_brain_states[brain_state_id]

            # Verify the brain state matches the model output
            assert brain_state == mock_agent_output.current_state

            # Verify the brain state ID was passed to extend function
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args[1]
            assert call_args["brain_state_id"] == brain_state_id

    @pytest.mark.asyncio
    async def test_after_step_hook_empty_implementation(
        self, navigator_agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test that after_step_hook has empty implementation"""
        # This should not raise any exception
        await navigator_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_before_action_hook_empty_implementation(
        self, navigator_agent, mock_action_model
    ) -> None:
        """Test that before_action_hook has empty implementation"""
        # This should not raise any exception
        await navigator_agent._before_action_hook(mock_action_model)

    @pytest.mark.asyncio
    async def test_after_action_hook_empty_implementation(
        self, navigator_agent, mock_action_model
    ) -> None:
        """Test that after_action_hook has empty implementation"""
        # This should not raise any exception
        await navigator_agent._after_action_hook(mock_action_model)

    def test_save_agent_actions_creates_directory(self, navigator_agent, tmp_path) -> None:
        """Test that save_agent_actions creates the traversals directory if it doesn't exist"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Initialize agent with some data
            navigator_agent.agent_taken_actions = [MagicMock(spec=BugninjaExtendedAction)]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test")}

            # Mock the traversal data
            with patch.object(navigator_agent, "_create_traversal_data") as mock_create:
                mock_create.return_value = MagicMock(spec=Traversal)

                navigator_agent.save_agent_actions()

                # Verify traversals directory was created
                assert Path("./traversals").exists()
                assert Path("./traversals").is_dir()

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_file_creation(self, navigator_agent, tmp_path) -> None:
        """Test that save_agent_actions creates a file with correct naming"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with some data
            mock_action = MagicMock(spec=BugninjaExtendedAction)
            mock_action.model_dump.return_value = {
                "action_type": "click",
                "selectors": {"css": "button"},
            }
            navigator_agent.agent_taken_actions = [mock_action]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test")}

            # Mock CUID generation
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                # Mock datetime
                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Verify file was created with correct naming
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename
                    assert expected_path.exists()

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_data_structure(self, navigator_agent, tmp_path) -> None:
        """Test that save_agent_actions creates correct data structure"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with test data
            mock_action = MagicMock(spec=BugninjaExtendedAction)
            mock_action.model_dump.return_value = {
                "brain_state_id": "brain_1",
                "action_type": "click",
                "selectors": {"css": "button"},
                "action_params": {"text": "Click me"},
                "element_attributes": {"tag_name": "button"},
                "context": "Testing",
                "assertion": {"type": "visible", "selector": "button"},
            }
            navigator_agent.agent_taken_actions = [mock_action]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test thought")}

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Read the saved file
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename

                    with open(expected_path, "r") as f:
                        saved_data = json.load(f)

                    # Verify data structure
                    assert "test_case" in saved_data
                    assert "browser_config" in saved_data
                    assert "secrets" in saved_data
                    assert "brain_states" in saved_data
                    assert "actions" in saved_data

                    # Verify specific values
                    assert saved_data["test_case"] == navigator_agent.task
                    assert saved_data["secrets"] == navigator_agent.sensitive_data
                    assert "brain_1" in saved_data["brain_states"]
                    assert "action_0" in saved_data["actions"]

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_verbose_logging(self, navigator_agent, tmp_path, caplog) -> None:
        """Test that save_agent_actions logs detailed information when verbose=True"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with test data
            mock_action = MagicMock(spec=BugninjaExtendedAction)
            mock_action.model_dump.return_value = {"action_type": "click"}
            navigator_agent.agent_taken_actions = [mock_action]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test")}

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions(verbose=True)

                    # Verify verbose logging
                    assert "Step 1:" in caplog.text
                    assert "Log:" in caplog.text

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_no_actions(self, navigator_agent, tmp_path) -> None:
        """Test save_agent_actions with no actions recorded"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with no actions
            navigator_agent.agent_taken_actions = []
            navigator_agent.agent_brain_states = {}

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Verify file was still created
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename
                    assert expected_path.exists()

                    # Read the saved file
                    with open(expected_path, "r") as f:
                        saved_data = json.load(f)

                    # Verify empty actions and brain states
                    assert saved_data["actions"] == {}
                    assert saved_data["brain_states"] == {}

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_multiple_actions(self, navigator_agent, tmp_path) -> None:
        """Test save_agent_actions with multiple actions"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with multiple actions
            mock_action1 = MagicMock(spec=BugninjaExtendedAction)
            mock_action1.model_dump.return_value = {
                "action_type": "click",
                "selectors": {"css": "button1"},
            }

            mock_action2 = MagicMock(spec=BugninjaExtendedAction)
            mock_action2.model_dump.return_value = {
                "action_type": "fill",
                "selectors": {"css": "input"},
            }

            mock_action3 = MagicMock(spec=BugninjaExtendedAction)
            mock_action3.model_dump.return_value = {
                "action_type": "submit",
                "selectors": {"css": "form"},
            }

            navigator_agent.agent_taken_actions = [mock_action1, mock_action2, mock_action3]
            navigator_agent.agent_brain_states = {
                "brain_1": AgentBrain(thought="First thought"),
                "brain_2": AgentBrain(thought="Second thought"),
                "brain_3": AgentBrain(thought="Third thought"),
            }

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Read the saved file
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename

                    with open(expected_path, "r") as f:
                        saved_data = json.load(f)

                    # Verify all actions were saved
                    assert "action_0" in saved_data["actions"]
                    assert "action_1" in saved_data["actions"]
                    assert "action_2" in saved_data["actions"]

                    # Verify action data
                    assert saved_data["actions"]["action_0"]["action_type"] == "click"
                    assert saved_data["actions"]["action_1"]["action_type"] == "fill"
                    assert saved_data["actions"]["action_2"]["action_type"] == "submit"

                    # Verify brain states
                    assert len(saved_data["brain_states"]) == 3

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_browser_config_conversion(self, navigator_agent, tmp_path) -> None:
        """Test that browser profile is properly converted to BugninjaBrowserConfig"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Set up browser profile with specific values
            navigator_agent.browser_profile.user_agent = "Test User Agent"
            navigator_agent.browser_profile.viewport = {"width": 1920, "height": 1080}
            navigator_agent.browser_profile.device_scale_factor = 2.0
            navigator_agent.browser_profile.timeout = 45000.0

            # Initialize agent with minimal data
            navigator_agent.agent_taken_actions = []
            navigator_agent.agent_brain_states = {}

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Read the saved file
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename

                    with open(expected_path, "r") as f:
                        saved_data = json.load(f)

                    # Verify browser config was properly converted
                    browser_config = saved_data["browser_config"]
                    assert browser_config["user_agent"] == "Test User Agent"
                    assert browser_config["viewport"] == {"width": 1920, "height": 1080}
                    assert browser_config["device_scale_factor"] == 2.0
                    assert browser_config["timeout"] == 45000.0

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_navigator_agent_inheritance(self, navigator_agent) -> None:
        """Test that NavigatorAgent properly inherits from BugninjaAgentBase"""
        from src.agents.bugninja_agent_base import BugninjaAgentBase

        # Verify inheritance
        assert isinstance(navigator_agent, BugninjaAgentBase)
        assert isinstance(navigator_agent, NavigatorAgent)

        # Verify all required methods are implemented
        assert hasattr(navigator_agent, "_before_step_hook")
        assert hasattr(navigator_agent, "_after_step_hook")
        assert hasattr(navigator_agent, "_before_run_hook")
        assert hasattr(navigator_agent, "_after_run_hook")
        assert hasattr(navigator_agent, "_before_action_hook")
        assert hasattr(navigator_agent, "_after_action_hook")

    @pytest.mark.asyncio
    async def test_navigator_agent_complete_workflow(
        self, navigator_agent, mock_browser_state_summary, mock_agent_output, mock_page
    ) -> None:
        """Test a complete workflow of the NavigatorAgent"""
        # Mock the browser session
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function
        mock_extended_action = MagicMock(spec=BugninjaExtendedAction)
        mock_extended_action.model_dump.return_value = {
            "brain_state_id": "test_brain_id",
            "action_type": "click",
            "selectors": {"css": "button"},
            "action_params": {"text": "Click me"},
            "element_attributes": {"tag_name": "button"},
            "context": "Testing",
            "assertion": {"type": "visible", "selector": "button"},
        }

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            # Execute the complete workflow
            await navigator_agent._before_run_hook()
            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await navigator_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify state was properly initialized
            assert hasattr(navigator_agent, "agent_taken_actions")
            assert hasattr(navigator_agent, "agent_brain_states")
            assert isinstance(navigator_agent.controller, BugninjaController)

            # Verify data was recorded
            assert len(navigator_agent.agent_taken_actions) == 1
            assert len(navigator_agent.agent_brain_states) == 1

            # Verify the recorded data
            recorded_action = navigator_agent.agent_taken_actions[0]
            assert recorded_action == mock_extended_action

            brain_state_id = list(navigator_agent.agent_brain_states.keys())[0]
            brain_state = navigator_agent.agent_brain_states[brain_state_id]
            assert brain_state == mock_agent_output.current_state

    def test_save_agent_actions_error_handling(self, navigator_agent, tmp_path) -> None:
        """Test error handling in save_agent_actions"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with test data
            navigator_agent.agent_taken_actions = [MagicMock(spec=BugninjaExtendedAction)]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test")}

            # Mock CUID to raise an exception
            with patch("cuid2.Cuid.generate", side_effect=Exception("CUID generation failed")):
                with pytest.raises(Exception, match="CUID generation failed"):
                    navigator_agent.save_agent_actions()

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_file_write_error(self, navigator_agent, tmp_path) -> None:
        """Test handling of file write errors in save_agent_actions"""
        # Change to temporary directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with test data
            navigator_agent.agent_taken_actions = [MagicMock(spec=BugninjaExtendedAction)]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrain(thought="Test")}

            # Mock CUID and datetime
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    # Mock json.dump to raise an exception
                    with patch("json.dump", side_effect=OSError("Disk full")):
                        with pytest.raises(OSError, match="Disk full"):
                            navigator_agent.save_agent_actions()

        finally:
            os.chdir(original_cwd)
