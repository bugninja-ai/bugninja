import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from browser_use.agent.views import AgentBrain, AgentOutput  # type: ignore
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from browser_use.dom.views import DOMElementNode  # type: ignore
from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.extensions import BugninjaController
from src.agents.navigator_agent import NavigatorAgent
from src.schemas.pipeline import BugninjaExtendedAction, Traversal

# Import Polyfactory factories for test data generation
from tests.fixtures.models.schema_factories import (
    AgentBrainFactory,
    BugninjaExtendedActionFactory,
)


class TestNavigatorAgent:
    """Test suite for `NavigatorAgent` class.

    This test suite validates the `NavigatorAgent` class which extends
    `BugninjaAgentBase` to provide navigation-specific functionality.
    These tests ensure that the agent properly initializes, records actions
    and brain states, and saves traversal data for replay scenarios.
    """

    @pytest.fixture
    def navigator_agent(self) -> NavigatorAgent:
        """Create a `NavigatorAgent` instance for testing.

        This fixture provides a properly initialized `NavigatorAgent` with
        all required attributes and mocked dependencies. The agent is configured
        with realistic settings for testing navigation scenarios and action
        recording functionality.
        """

        test_task: str = "Some random task to complete"
        llm_to_use = MagicMock(spec=BaseChatModel)

        # Enable LLM verification bypass for testing
        from src.agents.bugninja_agent_base import BugninjaAgentBase

        BugninjaAgentBase.BYPASS_LLM_VERIFICATION = True

        agent = NavigatorAgent(task=test_task, llm=llm_to_use)

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
    def mock_browser_state_summary(self) -> BrowserStateSummary:
        """Create a mock browser state summary for testing.

        This fixture provides a realistic `BrowserStateSummary` object with
        sample page data including URL, title, and element information.
        This data is essential for testing agent interactions with browser
        state during navigation scenarios.
        """

        return BrowserStateSummary(
            element_tree=DOMElementNode(
                is_visible=True,
                parent=None,
                tag_name="button",
                xpath="/html/body/div/button[@id='test-button']",
                attributes={"id": "test-button"},
                children=[],
            ),
            selector_map={
                0: DOMElementNode(
                    is_visible=True,
                    parent=None,
                    tag_name="button",
                    xpath="/html/body/div/button[@id='test-button']",
                    attributes={"id": "test-button"},
                    children=[],
                )
            },
            url="https://example.com",
            title="Test Page",
            tabs=[],
            screenshot=None,
            pixels_above=0,
            pixels_below=0,
            browser_errors=[],
        )

    @pytest.fixture
    def mock_agent_output(self) -> AgentOutput:
        """Create a mock agent output for testing.

        This fixture provides a realistic `AgentOutput` object with sample
        action data and brain state information. This data is crucial for
        testing how the agent processes and records action outputs during
        navigation scenarios.
        """
        return AgentOutput(
            action=[],
            current_state=AgentBrain(
                evaluation_previous_goal="Prev goal 1",
                memory="Test memory 1",
                next_goal="Next goal 1",
            ),
        )

    @pytest.fixture
    def mock_page(self) -> Page:
        """Create a mock page for testing.

        This fixture provides a realistic `Page` object with sample URL
        and title data. This data is essential for testing agent interactions
        with browser pages during navigation and action recording scenarios.
        """
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
        return page

    @pytest.fixture
    def mock_action_model(self) -> ActionModel:
        """Create a mock action model for testing.

        This fixture provides a realistic `ActionModel` object with sample
        action data including selectors and parameters. This data is crucial
        for testing how the agent processes and executes actions during
        navigation scenarios.
        """
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None
        return action

    @pytest.fixture
    def mock_bugninja_extended_action(self) -> BugninjaExtendedAction:
        """Create a mock BugninjaExtendedAction"""
        return BugninjaExtendedAction(
            brain_state_id="cs3zh3w5cx7e1f872il82sdf",
            action={
                "done": None,
                "search_google": None,
                "go_to_url": None,
                "go_back": None,
                "wait": None,
                "click_element_by_index": {"index": 6, "xpath": None},
                "input_text": None,
                "save_pdf": None,
                "switch_tab": None,
                "open_tab": None,
                "close_tab": None,
                "extract_content": None,
                "get_ax_tree": None,
                "scroll_down": None,
                "scroll_up": None,
                "send_keys": None,
                "scroll_to_text": None,
                "get_dropdown_options": None,
                "select_dropdown_option": None,
                "drag_drop": None,
            },
            dom_element_data={
                "tag_name": "button",
                "xpath": "html/body/div[1]/div/div[1]/div/div[2]/div[2]/form/button",
                "attributes": {
                    "class": "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow hover:bg-primary/90 dark:text-white h-9 px-4 py-2 w-full",
                    "type": "submit",
                    "data-umami-event": "login_button_click",
                },
                "is_visible": True,
                "is_interactive": True,
                "is_top_element": True,
                "is_in_viewport": True,
                "shadow_root": False,
                "highlight_index": 6,
                "viewport_coordinates": None,
                "page_coordinates": None,
                "children": [{"text": "Login", "type": "TEXT_NODE"}],
                "alternative_relative_xpaths": [
                    "//button[text()='Login']",
                    "//button[contains(@class, 'bg-primary')]",
                    "//button[contains(@class, 'text-primary-foreground')]",
                    "//button[contains(@class, 'hover:bg-primary/90')]",
                    "//button[contains(@class, 'dark:text-white')]",
                    "//form/button",
                    "//form[contains(@class, 'space-y-4')]/button",
                    "//div[contains(@class, 'rounded-lg')]/div[2]/form/button",
                    "//div[contains(@class, 'bg-card')]/div[2]/form/button",
                    "//div[contains(@class, 'text-card-foreground')]/div[2]/form/button",
                    "//div[contains(@class, 'shadow-sm')]/div[2]/form/button",
                    "//div[contains(@class, 'max-w-[400px]')]/div[2]/div[2]/form/button",
                    "//div[contains(@class, 'mx-4')]/div[2]/div[2]/form/button",
                    "//div[contains(@class, 'bg-background')]/div/div[1]/div/div[2]/div[2]/form/button",
                    "//body/div[1]/div/div[1]/div/div[2]/div[2]/form/button",
                    "//body[contains(@class, '__className_d65c78')]/div[1]/div/div[1]/div/div[2]/div[2]/form/button",
                    "//html/body/div[1]/div/div[1]/div/div[2]/div[2]/form/button",
                    "//html[contains(@class, 'light')]/body/div[1]/div/div[1]/div/div[2]/div[2]/form/button",
                ],
            },
        )

    @pytest.mark.asyncio
    async def test_before_run_hook_initialization(self, navigator_agent: NavigatorAgent) -> None:
        """Test that `_before_run_hook` properly initializes agent state.

        This test validates that the `_before_run_hook` method correctly
        initializes the agent's internal state for action recording and
        brain state tracking. Proper initialization is critical for ensuring
        that all navigation actions and brain states are properly recorded
        throughout the agent's execution lifecycle.
        """
        await navigator_agent._before_run_hook()

        # Verify agent state is initialized - critical for action and brain state tracking
        assert hasattr(
            navigator_agent, "agent_taken_actions"
        ), "Agent should have actions tracking list"
        assert hasattr(
            navigator_agent, "agent_brain_states"
        ), "Agent should have brain states tracking dict"
        assert isinstance(
            navigator_agent.agent_taken_actions, list
        ), "Actions should be stored as list"
        assert isinstance(
            navigator_agent.agent_brain_states, dict
        ), "Brain states should be stored as dict"
        assert (
            len(navigator_agent.agent_taken_actions) == 0
        ), "Actions list should be empty initially"
        assert (
            len(navigator_agent.agent_brain_states) == 0
        ), "Brain states dict should be empty initially"

        # Verify controller is overridden with BugninjaController - essential for proper action processing
        assert isinstance(
            navigator_agent.controller, BugninjaController
        ), "Controller should be BugninjaController instance"

    @pytest.mark.asyncio
    async def test_before_run_hook_controller_override(
        self, navigator_agent: NavigatorAgent
    ) -> None:
        """Test that the controller is properly overridden with `BugninjaController`.

        This test validates that the `_before_run_hook` method correctly
        overrides the default controller with a `BugninjaController` instance.
        This override is essential for ensuring that the agent uses the
        proper controller for processing navigation actions and maintaining
        compatibility with the bugninja framework.
        """
        # Set a different controller first to test override functionality
        navigator_agent.controller = MagicMock()

        await navigator_agent._before_run_hook()

        # Verify controller was replaced with BugninjaController - critical for proper action processing
        assert isinstance(
            navigator_agent.controller, BugninjaController
        ), "Controller should be overridden with BugninjaController"

    @pytest.mark.asyncio
    async def test_after_run_hook_calls_save_agent_actions(
        self, navigator_agent: NavigatorAgent
    ) -> None:
        """Test that `_after_run_hook` calls `save_agent_actions`.

        This test validates that the `_after_run_hook` method properly
        calls the `save_agent_actions` method to persist recorded actions
        and brain states. This persistence is critical for maintaining
        a complete record of navigation sessions for replay and analysis.
        """
        with patch.object(navigator_agent, "save_agent_actions") as mock_save:
            await navigator_agent._after_run_hook()

            # Verify save_agent_actions was called - essential for data persistence
            mock_save.assert_called_once(), "save_agent_actions should be called exactly once"

    @pytest.mark.asyncio
    async def test_before_step_hook_action_recording(
        self,
        navigator_agent: NavigatorAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that actions are properly recorded during step execution.

        This test validates that the `_before_step_hook` method correctly
        records both brain states and actions during step execution. This
        recording is critical for maintaining a complete audit trail of
        navigation decisions and actions for replay and debugging purposes.
        """
        # Initialize agent state - essential for action and brain state tracking
        await navigator_agent._before_run_hook()

        # Mock the browser session to provide current page information
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend_agent_action_with_info function to return realistic action data
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

            # Verify brain state was recorded - critical for maintaining decision history
            assert len(navigator_agent.agent_brain_states) == 1, "Should record one brain state"
            assert (
                mock_agent_output.current_state in navigator_agent.agent_brain_states.values()
            ), "Brain state should match agent output"

            # Verify action was recorded - essential for maintaining action history
            assert len(navigator_agent.agent_taken_actions) == 1, "Should record one action"
            assert (
                navigator_agent.agent_taken_actions[0] == mock_extended_action
            ), "Recorded action should match extended action"

            # Verify extend_agent_action_with_info was called with correct parameters - critical for action processing
            mock_extend.assert_called_once(), "extend_agent_action_with_info should be called once"
            call_args = mock_extend.call_args
            assert (
                call_args[1]["brain_state_id"] in navigator_agent.agent_brain_states
            ), "Brain state ID should be passed to extension"
            assert (
                call_args[1]["current_page"] == mock_page
            ), "Current page should be passed to extension"
            assert (
                call_args[1]["model_output"] == mock_agent_output
            ), "Model output should be passed to extension"
            assert (
                call_args[1]["browser_state_summary"] == mock_browser_state_summary
            ), "Browser state should be passed to extension"

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_actions(
        self,
        navigator_agent: NavigatorAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test recording multiple actions in a single step.

        This test validates that the `_before_step_hook` method correctly
        handles scenarios where multiple actions are generated in a single
        step. This is important for complex navigation scenarios where
        the agent needs to perform multiple related actions to achieve
        a single goal.
        """
        # Initialize agent state - essential for action tracking
        await navigator_agent._before_run_hook()

        # Mock the browser session to provide current page information
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Create multiple mock extended actions using Polyfactory for realistic data
        mock_action1 = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id",
            action={"click": {"selector": "button1"}},
            dom_element_data={"tag_name": "button"},
        )
        mock_action2 = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id",
            action={"fill": {"selector": "input", "text": "test"}},
            dom_element_data={"tag_name": "input"},
        )

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_action1, mock_action2]

            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify both actions were recorded - critical for maintaining complete action history
            assert len(navigator_agent.agent_taken_actions) == 2, "Should record both actions"
            assert (
                navigator_agent.agent_taken_actions[0] == mock_action1
            ), "First action should be recorded correctly"
            assert (
                navigator_agent.agent_taken_actions[1] == mock_action2
            ), "Second action should be recorded correctly"

    @pytest.mark.asyncio
    async def test_before_step_hook_brain_state_generation(
        self,
        navigator_agent: NavigatorAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that brain state IDs are properly generated and stored.

        This test validates that the `_before_step_hook` method correctly
        generates unique brain state IDs and stores brain states with
        proper associations. This is critical for maintaining the relationship
        between actions and the brain states that generated them for replay
        and debugging purposes.
        """
        # Initialize agent state - essential for brain state tracking
        await navigator_agent._before_run_hook()

        # Mock the browser session to provide current page information
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return realistic action data
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [BugninjaExtendedActionFactory.custom_build()]

            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was stored - critical for maintaining decision history
            assert len(navigator_agent.agent_brain_states) == 1, "Should store one brain state"

            # Get the brain state ID that was used - essential for verifying ID generation
            brain_state_id = list(navigator_agent.agent_brain_states.keys())[0]
            brain_state = navigator_agent.agent_brain_states[brain_state_id]

            # Verify the brain state matches the model output - critical for data integrity
            assert (
                brain_state == mock_agent_output.current_state
            ), "Brain state should match agent output"

            # Verify the brain state ID was passed to extend function - essential for action-brain state association
            mock_extend.assert_called_once(), "extend_agent_action_with_info should be called once"
            call_args = mock_extend.call_args[1]
            assert (
                call_args["brain_state_id"] == brain_state_id
            ), "Brain state ID should be passed to extension function"

    @pytest.mark.asyncio
    async def test_after_step_hook_empty_implementation(
        self,
        navigator_agent: NavigatorAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test that `_after_step_hook` has empty implementation.

        This test validates that the `_after_step_hook` method has an empty
        implementation and does not raise any exceptions when called. This
        is important for ensuring that the hook system works correctly
        even when no post-step processing is required.
        """
        # This should not raise any exception - essential for hook system stability
        await navigator_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_before_action_hook_empty_implementation(
        self, navigator_agent: NavigatorAgent, mock_action_model: ActionModel
    ) -> None:
        """Test that `_before_action_hook` has empty implementation.

        This test validates that the `_before_action_hook` method has an empty
        implementation and does not raise any exceptions when called. This
        is important for ensuring that the hook system works correctly
        even when no pre-action processing is required.
        """
        # This should not raise any exception - essential for hook system stability
        await navigator_agent._before_action_hook(mock_action_model)

    @pytest.mark.asyncio
    async def test_after_action_hook_empty_implementation(
        self, navigator_agent: NavigatorAgent, mock_action_model: ActionModel
    ) -> None:
        """Test that `_after_action_hook` has empty implementation.

        This test validates that the `_after_action_hook` method has an empty
        implementation and does not raise any exceptions when called. This
        is important for ensuring that the hook system works correctly
        even when no post-action processing is required.
        """
        # This should not raise any exception - essential for hook system stability
        await navigator_agent._after_action_hook(mock_action_model)

    def test_save_agent_actions_creates_directory(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test that `save_agent_actions` creates the traversals directory if it doesn't exist.

        This test validates that the `save_agent_actions` method properly
        creates the traversals directory when it doesn't exist. This is
        critical for ensuring that navigation data can be persisted even
        when the directory structure hasn't been set up beforehand.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock the traversal data creation
            with patch.object(navigator_agent, "_create_traversal_data") as mock_create:
                mock_create.return_value = MagicMock(spec=Traversal)

                navigator_agent.save_agent_actions()

                # Verify traversals directory was created - essential for data persistence
                assert Path("./traversals").exists(), "Traversals directory should be created"
                assert Path("./traversals").is_dir(), "Traversals should be a directory"

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_file_creation(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test that `save_agent_actions` creates a file with correct naming.

        This test validates that the `save_agent_actions` method creates
        files with proper naming conventions including timestamp and CUID.
        This naming is critical for ensuring unique file identification
        and proper organization of navigation data for replay scenarios.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock CUID generation for predictable testing
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                # Mock datetime for predictable file naming
                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Verify file was created with correct naming - essential for data organization
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename
                    assert expected_path.exists(), "File should be created with correct naming"

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_data_structure(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test that `save_agent_actions` creates correct data structure.

        This test validates that the `save_agent_actions` method creates
        files with the proper data structure including all required fields
        for traversal replay. This structure is critical for ensuring
        that saved navigation data can be properly loaded and replayed
        in future sessions.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock CUID and datetime for predictable testing
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

                    # Verify data structure - critical for replay functionality
                    assert "test_case" in saved_data, "test_case field should be present"
                    assert "browser_config" in saved_data, "browser_config field should be present"
                    assert "secrets" in saved_data, "secrets field should be present"
                    assert "brain_states" in saved_data, "brain_states field should be present"
                    assert "actions" in saved_data, "actions field should be present"

                    # Verify specific values - essential for data integrity
                    assert (
                        saved_data["test_case"] == navigator_agent.task
                    ), "test_case should match agent task"
                    assert (
                        saved_data["secrets"] == navigator_agent.sensitive_data
                    ), "secrets should match agent data"
                    assert (
                        "brain_1" in saved_data["brain_states"]
                    ), "brain_states should contain recorded brain state"
                    assert (
                        "action_0" in saved_data["actions"]
                    ), "actions should contain recorded action"

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_verbose_logging(
        self, navigator_agent: NavigatorAgent, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that `save_agent_actions` logs detailed information when verbose=True.

        This test validates that the `save_agent_actions` method provides
        detailed logging when verbose mode is enabled. This logging is
        critical for debugging navigation sessions and understanding
        the complete action sequence that was recorded.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock CUID and datetime for predictable testing
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions(verbose=True)

                    # Verify verbose logging - essential for debugging navigation sessions
                    assert "Step 1:" in caplog.text, "Should log step information"
                    assert "Log:" in caplog.text, "Should log action details"

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_no_actions(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test `save_agent_actions` with no actions recorded.

        This test validates that the `save_agent_actions` method handles
        edge cases where no actions have been recorded. This is important
        for ensuring that the method works correctly even when the agent
        hasn't performed any actions during the session.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with no actions - testing edge case
            navigator_agent.agent_taken_actions = []
            navigator_agent.agent_brain_states = {}

            # Mock CUID and datetime for predictable testing
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    navigator_agent.save_agent_actions()

                    # Verify file was still created - essential for edge case handling
                    expected_filename = "traverse_20231201_143022_test_cuid_123.json"
                    expected_path = traversals_dir / expected_filename
                    assert expected_path.exists(), "File should be created even with no actions"

                    # Read the saved file
                    with open(expected_path, "r") as f:
                        saved_data = json.load(f)

                    # Verify empty actions and brain states - critical for data integrity
                    assert saved_data["actions"] == {}, "Actions should be empty when none recorded"
                    assert (
                        saved_data["brain_states"] == {}
                    ), "Brain states should be empty when none recorded"

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_multiple_actions(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
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
                "brain_1": AgentBrain(
                    evaluation_previous_goal="Prev goal 1",
                    memory="Test memory 1",
                    next_goal="Next goal 1",
                ),
                "brain_2": AgentBrain(
                    evaluation_previous_goal="Prev goal 2",
                    memory="Test memory 2",
                    next_goal="Next goal 2",
                ),
                "brain_3": AgentBrain(
                    evaluation_previous_goal="Prev goal 3",
                    memory="Test memory 3",
                    next_goal="Next goal 3",
                ),
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

    def test_save_agent_actions_browser_config_conversion(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
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
    async def test_navigator_agent_inheritance(self, navigator_agent: NavigatorAgent) -> None:
        """Test that `NavigatorAgent` properly inherits from `BugninjaAgentBase`.

        This test validates that the `NavigatorAgent` class correctly
        inherits from `BugninjaAgentBase` and implements all required
        methods. This inheritance is critical for ensuring that the
        agent follows the proper interface and can be used within
        the bugninja framework.
        """
        from src.agents.bugninja_agent_base import BugninjaAgentBase

        # Verify inheritance - critical for framework compatibility
        assert isinstance(
            navigator_agent, BugninjaAgentBase
        ), "Should inherit from BugninjaAgentBase"
        assert isinstance(navigator_agent, NavigatorAgent), "Should be NavigatorAgent instance"

        # Verify all required methods are implemented - essential for interface compliance
        assert hasattr(navigator_agent, "_before_step_hook"), "Should implement _before_step_hook"
        assert hasattr(navigator_agent, "_after_step_hook"), "Should implement _after_step_hook"
        assert hasattr(navigator_agent, "_before_run_hook"), "Should implement _before_run_hook"
        assert hasattr(navigator_agent, "_after_run_hook"), "Should implement _after_run_hook"
        assert hasattr(
            navigator_agent, "_before_action_hook"
        ), "Should implement _before_action_hook"
        assert hasattr(navigator_agent, "_after_action_hook"), "Should implement _after_action_hook"

    @pytest.mark.asyncio
    async def test_navigator_agent_complete_workflow(
        self,
        navigator_agent: NavigatorAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test a complete workflow of the `NavigatorAgent`.

        This test validates the complete workflow of the `NavigatorAgent`
        including initialization, action recording, and state management.
        This integration test is critical for ensuring that all components
        work together correctly in a realistic navigation scenario.
        """
        # Mock the browser session to provide current page information
        navigator_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return realistic action data using Polyfactory
        mock_extended_action = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id",
            action={"click": {"selector": "button", "text": "Click me"}},
            dom_element_data={"tag_name": "button"},
        )

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            # Execute the complete workflow - critical for integration testing
            await navigator_agent._before_run_hook()
            await navigator_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await navigator_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify state was properly initialized - essential for workflow integrity
            assert hasattr(navigator_agent, "agent_taken_actions"), "Should have actions tracking"
            assert hasattr(
                navigator_agent, "agent_brain_states"
            ), "Should have brain states tracking"
            assert isinstance(
                navigator_agent.controller, BugninjaController
            ), "Should use BugninjaController"

            # Verify data was recorded - critical for maintaining complete session history
            assert len(navigator_agent.agent_taken_actions) == 1, "Should record one action"
            assert len(navigator_agent.agent_brain_states) == 1, "Should record one brain state"

            # Verify the recorded data - essential for data integrity
            recorded_action = navigator_agent.agent_taken_actions[0]
            assert (
                recorded_action == mock_extended_action
            ), "Recorded action should match extended action"

            brain_state_id = list(navigator_agent.agent_brain_states.keys())[0]
            brain_state = navigator_agent.agent_brain_states[brain_state_id]
            assert (
                brain_state == mock_agent_output.current_state
            ), "Brain state should match agent output"

    def test_save_agent_actions_error_handling(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test error handling in `save_agent_actions`.

        This test validates that the `save_agent_actions` method properly
        handles errors during the save process. This error handling is
        critical for ensuring that navigation sessions don't fail silently
        when encountering issues with file system operations or data generation.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock CUID to raise an exception - testing error propagation
            with patch("cuid2.Cuid.generate", side_effect=Exception("CUID generation failed")):
                with pytest.raises(Exception, match="CUID generation failed"):
                    navigator_agent.save_agent_actions()

        finally:
            os.chdir(original_cwd)

    def test_save_agent_actions_file_write_error(
        self, navigator_agent: NavigatorAgent, tmp_path: Path
    ) -> None:
        """Test handling of file write errors in `save_agent_actions`.

        This test validates that the `save_agent_actions` method properly
        handles file system errors during the save process. This error
        handling is critical for ensuring that navigation sessions fail
        gracefully when encountering disk space or permission issues.
        """
        # Change to temporary directory for isolated testing
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create traversals directory
            traversals_dir = Path("./traversals")
            traversals_dir.mkdir(exist_ok=True)

            # Initialize agent with realistic test data using Polyfactory
            navigator_agent.agent_taken_actions = [BugninjaExtendedActionFactory.custom_build()]
            navigator_agent.agent_brain_states = {"brain_1": AgentBrainFactory.custom_build()}

            # Mock CUID and datetime for predictable testing
            with patch("cuid2.Cuid.generate") as mock_cuid:
                mock_cuid.return_value = "test_cuid_123"

                with patch("datetime.datetime") as mock_datetime:
                    mock_datetime.now.return_value = datetime(2023, 12, 1, 14, 30, 22)
                    mock_datetime.strftime = datetime.strftime

                    # Mock json.dump to raise an exception - testing file system error handling
                    with patch("json.dump", side_effect=OSError("Disk full")):
                        with pytest.raises(OSError, match="Disk full"):
                            navigator_agent.save_agent_actions()

        finally:
            os.chdir(original_cwd)
