from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from browser_use.agent.views import AgentBrain, AgentOutput  # type:ignore
from browser_use.browser.session import Page  # type:ignore
from browser_use.browser.views import BrowserStateSummary  # type:ignore
from browser_use.controller.registry.views import ActionModel  # type:ignore
from cuid2 import Cuid as CUID

from src.agents.bugninja_agent_base import BugninjaAgentBase
from src.agents.extensions import BugninjaController
from src.agents.healer_agent import HealerAgent
from src.schemas.pipeline import BugninjaExtendedAction


class TestHealerAgent:
    """Test suite for HealerAgent class"""

    @pytest.fixture
    def healer_agent(self) -> HealerAgent:
        """Create a HealerAgent instance for testing"""
        agent = HealerAgent()

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
        agent.task = "Test healing task"

        # Mock action models
        agent.ActionModel = MagicMock()
        agent.DoneAgentOutput = MagicMock()

        # Mock callbacks
        agent.register_new_step_callback = None

        return agent

    @pytest.fixture
    def mock_browser_state_summary(self) -> BrowserStateSummary:
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
    def mock_agent_output(self) -> AgentOutput:
        """Create a mock agent output"""
        return AgentOutput(action=[], current_state=AgentBrain(thought="Test healing thought"))

    @pytest.fixture
    def mock_page(self) -> Page:
        """Create a mock page"""
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
        return page

    @pytest.fixture
    def mock_action_model(self) -> ActionModel:
        """Create a mock action model"""
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
    async def test_healer_agent_inheritance(self, healer_agent: HealerAgent) -> None:
        """Test that HealerAgent properly inherits from BugninjaAgentBase"""
        # Verify inheritance
        assert isinstance(healer_agent, BugninjaAgentBase)
        assert isinstance(healer_agent, HealerAgent)

        # Verify all required methods are implemented
        assert hasattr(healer_agent, "_before_step_hook")
        assert hasattr(healer_agent, "_after_step_hook")
        assert hasattr(healer_agent, "_before_run_hook")
        assert hasattr(healer_agent, "_after_run_hook")
        assert hasattr(healer_agent, "_before_action_hook")
        assert hasattr(healer_agent, "_after_action_hook")

    def test_healer_agent_initialization(self, healer_agent: HealerAgent) -> None:
        """Test that HealerAgent is properly initialized"""
        # Verify agent-specific attributes are initialized
        assert hasattr(healer_agent, "agent_taken_actions")
        assert hasattr(healer_agent, "agent_brain_states")
        assert isinstance(healer_agent.agent_taken_actions, list)
        assert isinstance(healer_agent.agent_brain_states, dict)
        assert len(healer_agent.agent_taken_actions) == 0
        assert len(healer_agent.agent_brain_states) == 0

    @pytest.mark.asyncio
    async def test_before_run_hook_initialization(self, healer_agent: HealerAgent) -> None:
        """Test that before_run_hook properly initializes agent state"""
        await healer_agent._before_run_hook()

        # Verify controller is overridden with BugninjaController
        assert isinstance(healer_agent.controller, BugninjaController)

    @pytest.mark.asyncio
    async def test_before_run_hook_controller_override(self, healer_agent: HealerAgent) -> None:
        """Test that the controller is properly overridden with BugninjaController"""
        # Set a different controller first
        healer_agent.controller = MagicMock()

        await healer_agent._before_run_hook()

        # Verify controller was replaced with BugninjaController
        assert isinstance(healer_agent.controller, BugninjaController)

    @pytest.mark.asyncio
    async def test_after_run_hook_empty_implementation(self, healer_agent: HealerAgent) -> None:
        """Test that after_run_hook has empty implementation"""
        # This should not raise any exception
        await healer_agent._after_run_hook()

    @pytest.mark.asyncio
    async def test_before_step_hook_action_recording(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that actions are properly recorded during step execution"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

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

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was recorded
            assert len(healer_agent.agent_brain_states) == 1
            assert mock_agent_output.current_state in healer_agent.agent_brain_states.values()

            # Verify action was recorded
            assert len(healer_agent.agent_taken_actions) == 1
            assert healer_agent.agent_taken_actions[0] == mock_extended_action

            # Verify extend_agent_action_with_info was called
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args
            assert call_args[1]["brain_state_id"] in healer_agent.agent_brain_states
            assert call_args[1]["current_page"] == mock_page
            assert call_args[1]["model_output"] == mock_agent_output
            assert call_args[1]["browser_state_summary"] == mock_browser_state_summary

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_actions(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test recording multiple actions in a single step"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

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

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify both actions were recorded
            assert len(healer_agent.agent_taken_actions) == 2
            assert healer_agent.agent_taken_actions[0] == mock_action1
            assert healer_agent.agent_taken_actions[1] == mock_action2

    @pytest.mark.asyncio
    async def test_before_step_hook_brain_state_generation(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that brain state IDs are properly generated and stored"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was stored
            assert len(healer_agent.agent_brain_states) == 1

            # Get the brain state ID that was used
            brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
            brain_state = healer_agent.agent_brain_states[brain_state_id]

            # Verify the brain state matches the model output
            assert brain_state == mock_agent_output.current_state

            # Verify the brain state ID was passed to extend function
            mock_extend.assert_called_once()
            call_args = mock_extend.call_args[1]
            assert call_args["brain_state_id"] == brain_state_id

    @pytest.mark.asyncio
    async def test_before_step_hook_cuid_generation(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that CUID is properly generated for brain state IDs"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock CUID generation
        with patch("cuid2.Cuid.generate") as mock_cuid:
            mock_cuid.return_value = "test_cuid_123"

            # Mock the extend function
            with patch(
                "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
            ) as mock_extend:
                mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

                # Verify CUID was generated
                mock_cuid.assert_called_once()

                # Verify the generated CUID was used as brain state ID
                brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
                assert brain_state_id == "test_cuid_123"

    @pytest.mark.asyncio
    async def test_before_step_hook_multiple_steps(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that multiple steps accumulate actions and brain states correctly"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

            # Execute multiple steps
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify actions and brain states accumulated
            assert len(healer_agent.agent_taken_actions) == 3
            assert len(healer_agent.agent_brain_states) == 3

            # Verify extend function was called for each step
            assert mock_extend.call_count == 3

    @pytest.mark.asyncio
    async def test_after_step_hook_empty_implementation(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test that after_step_hook has empty implementation"""
        # This should not raise any exception
        await healer_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_before_action_hook_empty_implementation(
        self, healer_agent: HealerAgent, mock_action_model: ActionModel
    ) -> None:
        """Test that before_action_hook has empty implementation"""
        # This should not raise any exception
        await healer_agent._before_action_hook(mock_action_model)

    @pytest.mark.asyncio
    async def test_after_action_hook_empty_implementation(
        self, healer_agent: HealerAgent, mock_action_model: ActionModel
    ) -> None:
        """Test that after_action_hook has empty implementation"""
        # This should not raise any exception
        await healer_agent._after_action_hook(mock_action_model)

    @pytest.mark.asyncio
    async def test_healer_agent_complete_workflow(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test a complete workflow of the HealerAgent"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

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
            await healer_agent._before_run_hook()
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._after_step_hook(mock_browser_state_summary, mock_agent_output)
            await healer_agent._after_run_hook()

            # Verify state was properly initialized
            assert hasattr(healer_agent, "agent_taken_actions")
            assert hasattr(healer_agent, "agent_brain_states")
            assert isinstance(healer_agent.controller, BugninjaController)

            # Verify data was recorded
            assert len(healer_agent.agent_taken_actions) == 1
            assert len(healer_agent.agent_brain_states) == 1

            # Verify the recorded data
            recorded_action = healer_agent.agent_taken_actions[0]
            assert recorded_action == mock_extended_action

            brain_state_id = list(healer_agent.agent_brain_states.keys())[0]
            brain_state = healer_agent.agent_brain_states[brain_state_id]
            assert brain_state == mock_agent_output.current_state

    @pytest.mark.asyncio
    async def test_healer_agent_difference_from_navigator_agent(
        self, healer_agent: HealerAgent
    ) -> None:
        """Test that HealerAgent differs from NavigatorAgent in specific ways"""
        from src.agents.navigator_agent import NavigatorAgent

        # Create a NavigatorAgent for comparison
        navigator_agent = NavigatorAgent()

        # Both should inherit from BugninjaAgentBase
        assert isinstance(healer_agent, BugninjaAgentBase)
        assert isinstance(navigator_agent, BugninjaAgentBase)

        # Both should have the same basic structure
        assert hasattr(healer_agent, "agent_taken_actions")
        assert hasattr(healer_agent, "agent_brain_states")
        assert hasattr(navigator_agent, "agent_taken_actions")
        assert hasattr(navigator_agent, "agent_brain_states")

        # Both should use BugninjaController
        await healer_agent._before_run_hook()
        await navigator_agent._before_run_hook()

        assert isinstance(healer_agent.controller, BugninjaController)
        assert isinstance(navigator_agent.controller, BugninjaController)

    @pytest.mark.asyncio
    async def test_healer_agent_action_recording_consistency(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that action recording is consistent across multiple calls"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return consistent data
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

            # Execute multiple steps with the same data
            for i in range(3):
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify consistent recording
            assert len(healer_agent.agent_taken_actions) == 3
            assert len(healer_agent.agent_brain_states) == 3

            # Verify all actions are the same
            for action in healer_agent.agent_taken_actions:
                assert action == mock_extended_action

            # Verify all brain states are the same
            for brain_state in healer_agent.agent_brain_states.values():
                assert brain_state == mock_agent_output.current_state

    @pytest.mark.asyncio
    async def test_healer_agent_error_handling_in_before_step_hook(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test error handling in before_step_hook"""
        # Mock browser session to raise an exception
        healer_agent.browser_session.get_current_page = AsyncMock(
            side_effect=Exception("Browser error")
        )

        # Test that the exception is properly raised
        with pytest.raises(Exception, match="Browser error"):
            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_healer_agent_error_handling_in_extend_function(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test error handling when extend_agent_action_with_info fails"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to raise an exception
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.side_effect = Exception("Extension error")

            # Test that the exception is properly raised
            with pytest.raises(Exception, match="Extension error"):
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

    @pytest.mark.asyncio
    async def test_healer_agent_empty_extend_result(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test handling when extend_agent_action_with_info returns empty result"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock the extend function to return empty list
        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = []

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

            # Verify brain state was still recorded
            assert len(healer_agent.agent_brain_states) == 1

            # Verify no actions were recorded
            assert len(healer_agent.agent_taken_actions) == 0

    @pytest.mark.asyncio
    async def test_healer_agent_brain_state_uniqueness(
        self,
        healer_agent: HealerAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_page: Page,
    ) -> None:
        """Test that brain state IDs are unique across multiple steps"""
        # Mock the browser session
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        # Mock CUID to return different values
        with patch("cuid2.Cuid.generate") as mock_cuid:
            mock_cuid.side_effect = ["cuid_1", "cuid_2", "cuid_3"]

            # Mock the extend function
            with patch(
                "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
            ) as mock_extend:
                mock_extend.return_value = [MagicMock(spec=BugninjaExtendedAction)]

                # Execute multiple steps
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
                await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)

                # Verify unique brain state IDs
                brain_state_ids = list(healer_agent.agent_brain_states.keys())
                assert len(brain_state_ids) == 3
                assert len(set(brain_state_ids)) == 3  # All IDs are unique
                assert "cuid_1" in brain_state_ids
                assert "cuid_2" in brain_state_ids
                assert "cuid_3" in brain_state_ids

    @pytest.mark.asyncio
    async def test_healer_agent_inheritance_chain(self, healer_agent: HealerAgent) -> None:
        """Test the complete inheritance chain of HealerAgent"""
        from src.agents.navigator_agent import NavigatorAgent

        # Verify inheritance chain
        assert isinstance(healer_agent, BugninjaAgentBase)
        assert isinstance(healer_agent, HealerAgent)

        # HealerAgent should NOT inherit from NavigatorAgent (as per comment in code)
        assert not isinstance(healer_agent, NavigatorAgent)

        # Both should have similar structure but be different classes
        navigator_agent = NavigatorAgent()
        assert isinstance(navigator_agent, BugninjaAgentBase)
        assert isinstance(navigator_agent, NavigatorAgent)
        assert not isinstance(navigator_agent, HealerAgent)

    @pytest.mark.asyncio
    async def test_healer_agent_method_resolution_order(self, healer_agent: HealerAgent) -> None:
        """Test the method resolution order of HealerAgent"""
        # Get the MRO
        mro = HealerAgent.__mro__

        # Verify the order
        assert mro[0] == HealerAgent
        assert BugninjaAgentBase in mro
        assert mro.index(HealerAgent) < mro.index(BugninjaAgentBase)

    @pytest.mark.asyncio
    async def test_healer_agent_constructor_args(self) -> None:
        """Test that HealerAgent constructor accepts the same args as parent"""
        # Test with various argument combinations
        agent1 = HealerAgent()
        assert isinstance(agent1, HealerAgent)

        # Test that it can be instantiated with parent class arguments
        # (This would depend on the actual parent class constructor)
        agent2 = HealerAgent()
        assert isinstance(agent2, HealerAgent)

    @pytest.mark.asyncio
    async def test_healer_agent_logging(self, healer_agent, caplog) -> None:
        """Test that HealerAgent logs appropriate messages"""
        # Test before_run_hook logging
        await healer_agent._before_run_hook()
        assert "BEFORE-Run hook called" in caplog.text

        # Test before_step_hook logging
        mock_browser_state_summary = MagicMock()
        mock_agent_output = MagicMock()
        mock_page = MagicMock()
        healer_agent.browser_session.get_current_page = AsyncMock(return_value=mock_page)

        with patch(
            "src.agents.extensions.extend_agent_action_with_info", new_callable=AsyncMock
        ) as mock_extend:
            mock_extend.return_value = []

            await healer_agent._before_step_hook(mock_browser_state_summary, mock_agent_output)
            assert "BEFORE-Step hook called" in caplog.text
