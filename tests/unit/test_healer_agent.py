from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from browser_use.agent.views import (  # type:ignore
    AgentBrain,
    AgentOutput,
    DOMElementNode,
)
from browser_use.browser.session import Page  # type:ignore
from browser_use.browser.views import BrowserStateSummary  # type:ignore
from browser_use.controller.registry.views import ActionModel  # type:ignore
from langchain_core.language_models.chat_models import BaseChatModel

from bugninja.agents import BugninjaAgentBase, BugninjaController, HealerAgent
from bugninja.schemas import BugninjaExtendedAction


class TestHealerAgent:
    """Test suite for HealerAgent class - validates inheritance, initialization, and action recording functionality"""

    @pytest.fixture
    def healer_agent(self) -> HealerAgent:
        """Create a HealerAgent instance for testing with all required attributes initialized"""

        test_task: str = "Some random task to complete"
        llm_to_use = MagicMock(spec=BaseChatModel)

        agent = HealerAgent(llm=llm_to_use, task=test_task)

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
        agent.browser_profile.wait_between_actions = 0.1

        agent.sensitive_data = {"test_key": "test_value"}
        agent.context = {}
        agent.tool_calling_method = "raw"
        agent.task = "Test healing task"

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
        """Create a mock agent output with test brain state for validation"""
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
        """Create a mock page for testing browser session interactions"""
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
        return page

    @pytest.fixture
    def mock_action_model(self) -> ActionModel:
        """Create a mock action model for testing action execution"""
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None
        return action

    @pytest.fixture
    def mock_bugninja_extended_action(self) -> BugninjaExtendedAction:
        """Create a comprehensive mock BugninjaExtendedAction for testing action recording"""
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
            idx_in_brainstate=0,
            screenshot_filename="screenshot.png",
        )

    @pytest.mark.asyncio
    async def test_healer_agent_inheritance_and_required_methods(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test that HealerAgent properly inherits from BugninjaAgentBase and implements all required methods

        This test validates the inheritance chain and ensures all abstract methods from the base class
        are properly implemented. This is critical for reliability as it ensures the agent can be
        instantiated and used without NotImplementedError exceptions.
        """
        # Verify inheritance chain is correct
        assert isinstance(
            healer_agent, BugninjaAgentBase
        ), "HealerAgent must inherit from BugninjaAgentBase to maintain the agent hierarchy"
        assert isinstance(
            healer_agent, HealerAgent
        ), "Agent should be an instance of HealerAgent for proper type checking"

        # Verify all required hook methods are implemented to prevent runtime errors
        assert hasattr(
            healer_agent, "_before_step_hook"
        ), "HealerAgent must implement _before_step_hook for step lifecycle management"
        assert hasattr(
            healer_agent, "_after_step_hook"
        ), "HealerAgent must implement _after_step_hook for step lifecycle management"
        assert hasattr(
            healer_agent, "_before_run_hook"
        ), "HealerAgent must implement _before_run_hook for run lifecycle management"
        assert hasattr(
            healer_agent, "_after_run_hook"
        ), "HealerAgent must implement _after_run_hook for run lifecycle management"
        assert hasattr(
            healer_agent, "_before_action_hook"
        ), "HealerAgent must implement _before_action_hook for action lifecycle management"
        assert hasattr(
            healer_agent, "_after_action_hook"
        ), "HealerAgent must implement _after_action_hook for action lifecycle management"

    def test_healer_agent_initialization_and_state_management(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test that HealerAgent is properly initialized with correct state management attributes

        This test validates that the agent starts with the correct initial state for tracking
        actions and brain states. This is essential for reliability as it ensures the agent
        can properly record and manage its execution history.
        """
        # Verify agent-specific tracking attributes are properly initialized
        assert hasattr(
            healer_agent, "agent_taken_actions"
        ), "HealerAgent must have agent_taken_actions attribute for action tracking"
        assert hasattr(
            healer_agent, "agent_brain_states"
        ), "HealerAgent must have agent_brain_states attribute for brain state tracking"
        assert isinstance(
            healer_agent.agent_taken_actions, list
        ), "agent_taken_actions must be a list for proper action accumulation"
        assert isinstance(
            healer_agent.agent_brain_states, dict
        ), "agent_brain_states must be a dict for proper brain state mapping"
        assert (
            len(healer_agent.agent_taken_actions) == 0
        ), "agent_taken_actions should start empty for clean state management"
        assert (
            len(healer_agent.agent_brain_states) == 0
        ), "agent_brain_states should start empty for clean state management"

    @pytest.mark.asyncio
    async def test_before_run_hook_controller_initialization(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test that before_run_hook properly initializes the BugninjaController for agent execution

        This test validates that the agent uses the correct controller type for browser interactions.
        This is critical for reliability as it ensures the agent can properly execute browser actions
        and maintain compatibility with the browser automation framework.
        """
        await healer_agent._before_run_hook()

        # Verify controller is properly initialized with the correct type
        assert isinstance(
            healer_agent.controller, BugninjaController
        ), "HealerAgent must use BugninjaController for proper browser control"

    @pytest.mark.asyncio
    async def test_before_run_hook_controller_override_behavior(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test that the controller is properly overridden with BugninjaController even when previously set

        This test validates the controller replacement logic ensures consistent controller type
        regardless of previous state. This is important for reliability as it prevents controller
        type mismatches that could cause runtime errors.
        """
        # Set a different controller first to test override behavior
        healer_agent.controller = MagicMock()

        await healer_agent._before_run_hook()

        # Verify controller was properly replaced with the correct type
        assert isinstance(
            healer_agent.controller, BugninjaController
        ), "Controller must be replaced with BugninjaController regardless of previous state"

    @pytest.mark.asyncio
    async def test_hook_methods_empty_implementations(self, healer_agent: HealerAgent) -> None:
        """Test that hook methods with empty implementations execute without errors

        This test validates that empty hook implementations don't cause runtime errors.
        This is important for reliability as it ensures the agent can execute all lifecycle
        methods without breaking the execution flow.
        """
        # Test that empty implementations don't raise exceptions
        await healer_agent._after_run_hook()
        await healer_agent._before_action_hook(MagicMock())
        await healer_agent._after_action_hook(MagicMock())

    @pytest.mark.asyncio
    async def test_before_step_hook_action_and_brain_state_recording(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that actions and brain states are properly recorded during step execution

        This test validates the core functionality of HealerAgent - recording agent actions
        and brain states for later analysis. This is critical for reliability as it ensures
        the agent can maintain a complete execution history for debugging and optimization.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend_agent_action_with_info function to return test data
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
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was properly recorded for analysis
            assert (
                len(healer_agent.agent_brain_states) == 1
            ), "Brain state should be recorded for step analysis"
            assert (
                mock_agent_output.current_state in healer_agent.agent_brain_states.values()
            ), "Recorded brain state should match the model output"

            # Verify action was properly recorded for execution history
            assert (
                len(healer_agent.agent_taken_actions) == 1
            ), "Action should be recorded for execution tracking"
            assert (
                healer_agent.agent_taken_actions[0] == mock_extended_action
            ), "Recorded action should match the extended action data"

            # Verify extend_agent_action_with_info was called with correct parameters
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args
            assert (
                call_args[1]["brain_state_id"] in healer_agent.agent_brain_states
            ), "Brain state ID should be passed to extension function"
            assert (
                call_args[1]["current_page"] == mock_page
            ), "Current page should be passed to extension function"
            assert (
                call_args[1]["model_output"] == mock_agent_output
            ), "Model output should be passed to extension function"
            assert (
                call_args[1]["browser_state_summary"] == mock_browser_state_summary
            ), "Browser state summary should be passed to extension function"

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_actions_recording(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test recording multiple actions in a single step for complex execution scenarios

        This test validates that the agent can handle multiple actions per step, which is
        important for complex workflows. This ensures reliability in scenarios where the
        agent needs to perform multiple related actions in sequence.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Create multiple mock extended actions to simulate complex step
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
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_action1, mock_action2]

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify both actions were properly recorded in order
            assert (
                len(healer_agent.agent_taken_actions) == 2
            ), "Multiple actions should be recorded for complex steps"
            assert (
                healer_agent.agent_taken_actions[0] == mock_action1
            ), "First action should be recorded in correct order"
            assert (
                healer_agent.agent_taken_actions[1] == mock_action2
            ), "Second action should be recorded in correct order"

    @pytest.mark.asyncio
    async def test_before_step_hook_brain_state_id_generation_and_storage(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that brain state IDs are properly generated and stored for state tracking

        This test validates the brain state ID generation mechanism, which is critical for
        tracking agent decision-making over time. This ensures reliability in scenarios
        where the agent needs to reference previous brain states for context.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return test data
        with patch(
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was properly stored with unique ID
            assert (
                len(healer_agent.agent_brain_states) == 1
            ), "Brain state should be stored for state tracking"

            # Get the brain state ID that was used and verify it's properly mapped
            brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
            brain_state = healer_agent.agent_brain_states[brain_state_id]

            # Verify the brain state mapping is correct
            assert (
                brain_state == mock_agent_output.current_state
            ), "Stored brain state should match the model output exactly"

            # Verify the brain state ID was passed to extension function
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args[1]
            assert (
                call_args["brain_state_id"] == brain_state_id
            ), "Generated brain state ID should be passed to extension function"

    @pytest.mark.asyncio
    async def test_before_step_hook_cuid_generation_for_brain_state_ids(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that CUID is properly generated for brain state IDs to ensure uniqueness

        This test validates the CUID generation mechanism for brain state IDs, which is
        critical for ensuring unique identification of brain states. This ensures reliability
        in scenarios where multiple brain states need to be distinguished.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock CUID generation to return predictable test value
        with patch("cuid2.Cuid.generate") as mock_cuid:
            mock_cuid.return_value = "test_cuid_123"

            # Mock the extend function to return test data
            with patch(
                "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
            ) as mock_extend:
                mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

                # Verify CUID was generated for brain state ID
                mock_cuid.assert_called_once()

                # Verify the generated CUID was used as brain state ID
                brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
                assert (
                    brain_state_id == "test_cuid_123"
                ), "Generated CUID should be used as brain state ID"

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_steps_accumulation(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that multiple steps accumulate actions and brain states correctly for execution history

        This test validates the accumulation behavior across multiple steps, which is
        critical for maintaining complete execution history. This ensures reliability
        in scenarios where the agent needs to reference its complete execution path.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return consistent test data
        with patch(
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

            # Execute multiple steps to test accumulation
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify actions and brain states accumulated correctly
            assert (
                len(healer_agent.agent_taken_actions) == 3
            ), "Actions should accumulate across multiple steps"
            assert (
                len(healer_agent.agent_brain_states) == 3
            ), "Brain states should accumulate across multiple steps"

            # Verify extend function was called for each step
            assert mock_extend.call_count == 3, "Extension function should be called for each step"

    @pytest.mark.asyncio
    async def test_after_step_hook_empty_implementation_execution(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test that after_step_hook executes without errors despite empty implementation

        This test validates that empty hook implementations don't break the execution flow.
        This is important for reliability as it ensures the agent can complete all lifecycle
        methods without runtime errors.
        """
        # Test that empty implementation executes without raising exceptions
        await healer_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_healer_agent_complete_workflow_execution(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test a complete workflow of the HealerAgent to validate end-to-end functionality

        This test validates the complete lifecycle of the HealerAgent, ensuring all
        components work together correctly. This is critical for reliability as it
        tests the agent's ability to execute a full workflow without errors.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return comprehensive test data
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
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            # Execute the complete workflow to test all components
            await healer_agent._before_run_hook()
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._after_run_hook()

            # Verify state was properly initialized and maintained
            assert hasattr(
                healer_agent, "agent_taken_actions"
            ), "Agent should have action tracking capability"
            assert hasattr(
                healer_agent, "agent_brain_states"
            ), "Agent should have brain state tracking capability"
            assert isinstance(
                healer_agent.controller, BugninjaController
            ), "Agent should use correct controller type"

            # Verify data was properly recorded during workflow
            assert (
                len(healer_agent.agent_taken_actions) == 1
            ), "Workflow should record executed actions"
            assert len(healer_agent.agent_brain_states) == 1, "Workflow should record brain states"

            # Verify the recorded data matches expectations
            recorded_action = healer_agent.agent_taken_actions[0]
            assert (
                recorded_action == mock_extended_action
            ), "Recorded action should match the extended action data"

            brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
            brain_state = healer_agent.agent_brain_states[brain_state_id]
            assert (
                brain_state == mock_agent_output.current_state
            ), "Recorded brain state should match the model output"

    @pytest.mark.asyncio
    async def test_healer_agent_action_recording_consistency_across_multiple_calls(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that action recording is consistent across multiple calls for reliable tracking

        This test validates the consistency of action recording across multiple executions,
        which is critical for reliable debugging and analysis. This ensures that the agent
        maintains consistent behavior regardless of how many times it's called.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return consistent data across calls
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
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [mock_extended_action]

            # Execute multiple steps with the same data to test consistency
            for i in range(3):
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify consistent recording across all calls
            assert (
                len(healer_agent.agent_taken_actions) == 3
            ), "All actions should be recorded consistently"
            assert (
                len(healer_agent.agent_brain_states) == 3
            ), "All brain states should be recorded consistently"

            # Verify all actions are recorded consistently
            for action in healer_agent.agent_taken_actions:
                assert action == mock_extended_action, "All recorded actions should be consistent"

            # Verify all brain states are recorded consistently
            for brain_state in healer_agent.agent_brain_states.values():
                assert (
                    brain_state == mock_agent_output.current_state
                ), "All recorded brain states should be consistent"

    @pytest.mark.asyncio
    async def test_healer_agent_error_handling_in_before_step_hook_browser_session_failure(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test error handling when browser session fails during step execution

        This test validates that the agent properly handles browser session failures,
        which is critical for reliability in scenarios where the browser becomes
        unresponsive or encounters network issues.
        """
        # Mock browser session to raise an exception to simulate failure
        healer_agent.browser_session.get_current_page = AsyncMock(
            side_effect=Exception("Browser error")
        )

        # Test that the exception is properly raised and not swallowed
        with pytest.raises(Exception, match="Browser error"):
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_healer_agent_error_handling_in_extend_function_failure(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test error handling when extend_agent_action_with_info fails during action processing

        This test validates that the agent properly handles extension function failures,
        which is critical for reliability in scenarios where the action extension
        mechanism encounters errors.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to raise an exception to simulate failure
        with patch(
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.side_effect = Exception("Extension error")

            # Test that the exception is properly raised and not swallowed
            with pytest.raises(Exception, match="Extension error"):
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_healer_agent_empty_extend_result_handling(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test handling when extend_agent_action_with_info returns empty result

        This test validates that the agent properly handles cases where no actions
        are returned by the extension function. This is important for reliability
        in scenarios where the agent needs to handle empty action lists gracefully.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return empty list to simulate no actions
        with patch(
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = []

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was still recorded even with no actions
            assert (
                len(healer_agent.agent_brain_states) == 1
            ), "Brain state should be recorded even when no actions are returned"

            # Verify no actions were recorded when none are returned
            assert (
                len(healer_agent.agent_taken_actions) == 0
            ), "No actions should be recorded when extension returns empty list"

    @pytest.mark.asyncio
    async def test_healer_agent_brain_state_id_uniqueness_across_multiple_steps(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that brain state IDs are unique across multiple steps for proper state tracking

        This test validates the uniqueness of brain state IDs across multiple steps,
        which is critical for proper state tracking and debugging. This ensures
        that each brain state can be uniquely identified in the execution history.
        """
        # Mock the browser session for page access
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock CUID to return different values for each step
        with patch("cuid2.Cuid.generate") as mock_cuid:
            mock_cuid.side_effect = ["cuid_1", "cuid_2", "cuid_3"]

            # Mock the extend function to return test data
            with patch(
                "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
            ) as mock_extend:
                mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

                # Execute multiple steps to test ID uniqueness
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

                # Verify unique brain state IDs were generated
                brain_state_ids = list(healer_agent.agent_brain_states.keys())
                assert len(brain_state_ids) == 3, "Three brain state IDs should be generated"
                assert len(set(brain_state_ids)) == 3, "All brain state IDs should be unique"
                assert "cuid_1" in brain_state_ids, "First CUID should be used as brain state ID"
                assert "cuid_2" in brain_state_ids, "Second CUID should be used as brain state ID"
                assert "cuid_3" in brain_state_ids, "Third CUID should be used as brain state ID"

    @pytest.mark.asyncio
    async def test_healer_agent_method_resolution_order_and_inheritance_chain(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test the method resolution order and inheritance chain of HealerAgent

        This test validates the inheritance structure and method resolution order,
        which is critical for understanding how the agent resolves method calls
        and maintains proper inheritance relationships.
        """
        # Get the method resolution order to validate inheritance chain
        mro = HealerAgent.__mro__

        # Verify the inheritance order is correct
        assert mro[0] == HealerAgent, "HealerAgent should be the first class in MRO"
        assert BugninjaAgentBase in mro, "BugninjaAgentBase should be in the inheritance chain"
        assert mro.index(HealerAgent) < mro.index(
            BugninjaAgentBase
        ), "HealerAgent should come before BugninjaAgentBase in MRO"

    @pytest.mark.asyncio
    async def test_healer_agent_logging_behavior(
        self, healer_agent: HealerAgent, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that HealerAgent logs appropriate messages for debugging and monitoring

        This test validates the logging behavior of the HealerAgent, which is
        critical for debugging and monitoring agent execution. This ensures
        that important events are properly logged for analysis.
        """
        # Test before_run_hook logging behavior
        await healer_agent._before_run_hook()
        assert "BEFORE-Run hook called" in caplog.text, "Before run hook should log its execution"

        # Test before_step_hook logging behavior
        mock_browser_state_summary = MagicMock()
        mock_agent_output = MagicMock()
        mock_page = MagicMock()
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        with patch(
            "bugninja.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = []

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            assert (
                "BEFORE-Step hook called" in caplog.text
            ), "Before step hook should log its execution"
