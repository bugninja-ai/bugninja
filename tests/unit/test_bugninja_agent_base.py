from typing import Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from browser_use.agent.views import (  # type:ignore
    ActionResult,
    AgentBrain,
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.views import BrowserStateSummary  # type:ignore
from browser_use.controller.registry.views import ActionModel  # type:ignore
from browser_use.dom.views import DOMElementNode  # type: ignore
from langchain_core.messages import BaseMessage, HumanMessage
from patchright.async_api import Page  # type:ignore

from src.agents import BugninjaAgentBase


class ConcreteBugninjaAgent(BugninjaAgentBase):
    """Concrete implementation of BugninjaAgentBase for testing."""

    def __init__(self) -> None:
        self.before_step_called = False
        self.after_step_called = False
        self.before_run_called = False
        self.after_run_called = False
        self.before_action_called = False
        self.after_action_called = False
        self.hook_calls: List[Tuple[str, ...]] = []

        # Initialize required attributes
        self.state = MagicMock()
        self.state.n_steps = 0
        self.state.last_result = []
        self.state.consecutive_failures = 0

        self.settings = MagicMock()
        self.settings.use_vision = False
        self.settings.planner_interval = 5
        self.settings.save_conversation_path = None
        self.settings.save_conversation_path_encoding = "utf-8"

        self.browser_session = MagicMock()
        self.controller = MagicMock()
        self._message_manager = MagicMock()
        self.memory = MagicMock()
        self.enable_memory = False
        self.browser_profile.wait_between_actions = 0.1

        self.sensitive_data: Dict[str, str] = {}
        self.tool_calling_method = "raw"

        # Mock action models
        self.ActionModel = MagicMock()
        self.DoneAgentOutput = MagicMock()

    async def _before_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None:
        self.before_step_called = True
        self.hook_calls.append(("before_step", browser_state_summary, model_output))

    async def _after_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None:
        self.after_step_called = True
        self.hook_calls.append(("after_step", browser_state_summary, model_output))

    async def _before_run_hook(self) -> None:
        self.before_run_called = True
        self.hook_calls.append(("before_run",))

    async def _after_run_hook(self) -> None:
        self.after_run_called = True
        self.hook_calls.append(("after_run",))

    async def _before_action_hook(self, action: ActionModel) -> None:
        self.before_action_called = True
        self.hook_calls.append(("before_action", action))

    async def _after_action_hook(self, action: ActionModel) -> None:
        self.after_action_called = True
        self.hook_calls.append(("after_action", action))

    async def get_next_action(self, messages: List[BaseMessage]) -> AgentOutput:
        # Mock implementation for testing
        return AgentOutput(
            action=[],
            current_state=AgentBrain(
                evaluation_previous_goal="Prev goal 1",
                memory="Test memory 1",
                next_goal="Next goal 1",
            ),
        )


class TestBugninjaAgentBase:
    """Test suite for BugninjaAgentBase class. Validates hooks, step/run logic, and error handling."""

    @pytest.fixture
    def agent(self) -> ConcreteBugninjaAgent:
        """Create a concrete BugninjaAgentBase instance for testing."""
        from src.agents import BugninjaAgentBase

        BugninjaAgentBase.BYPASS_LLM_VERIFICATION = True
        return ConcreteBugninjaAgent()

    @pytest.fixture
    def mock_page(self) -> Page:
        """Create a mock page for Playwright page tests."""
        page = MagicMock(spec=Page)
        page.wait_for_load_state = AsyncMock()
        page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
        return page

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
        """Create a mock agent output for action/brain state tests."""
        return AgentOutput(
            action=[],
            current_state=AgentBrain(
                evaluation_previous_goal="Prev goal 1",
                memory="Test memory 1",
                next_goal="Next goal 1",
            ),
        )

    @pytest.fixture
    def mock_action_model(self) -> ActionModel:
        """Create a mock action model for action execution tests."""
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None
        return action

    @pytest.mark.asyncio
    async def test_get_raw_html_of_playwright_page_success(
        self, agent: ConcreteBugninjaAgent, mock_page: Page
    ) -> None:
        """Test successful HTML extraction from Playwright page.
        Ensures the agent waits for load and fetches content as expected."""
        html_content = await agent.get_raw_html_of_playwright_page(mock_page)
        assert (
            html_content == "<html><body>Test Content</body></html>"
        ), "HTML content should match the mocked return value"
        mock_page.wait_for_load_state.assert_has_calls(
            [call("domcontentloaded"), call("load")]
        ), "Should wait for both DOM and load states"
        mock_page.content.assert_called_once(), "Should call content() exactly once"

    @pytest.mark.asyncio
    async def test_get_raw_html_of_playwright_page_with_custom_content(
        self, agent: ConcreteBugninjaAgent
    ) -> None:
        """Test HTML extraction with custom content for Playwright page."""
        custom_html = "<html><body><h1>Custom Content</h1></body></html>"
        page = MagicMock()
        page.wait_for_load_state = AsyncMock()
        page.content = AsyncMock(return_value=custom_html)
        html_content = await agent.get_raw_html_of_playwright_page(page)
        assert html_content == custom_html, "HTML content should match the custom mocked value"

    @pytest.mark.asyncio
    async def test_run_method_execution_flow(self, agent: ConcreteBugninjaAgent) -> None:
        """Test the complete run method execution flow, including before/after hooks and parent run call."""
        with patch.object(BugninjaAgentBase, "run", new_callable=AsyncMock) as mock_parent_run:
            mock_parent_run.return_value = MagicMock(spec=AgentHistoryList)
            await agent.run(max_steps=10)
            assert agent.before_run_called, "before_run_called should be True after run()"
            assert agent.after_run_called, "after_run_called should be True after run()"
            mock_parent_run.assert_called_once_with(
                max_steps=10, on_step_start=None, on_step_end=None
            ), "Parent run should be called with correct parameters"
            assert agent.hook_calls[0][0] == "before_run", "First hook call should be before_run"
            assert agent.hook_calls[-1][0] == "after_run", "Last hook call should be after_run"

    @pytest.mark.asyncio
    async def test_run_method_with_different_max_steps(self, agent: ConcreteBugninjaAgent) -> None:
        """Test run method with different max_steps values to ensure parameter passing."""
        with patch.object(BugninjaAgentBase, "run", new_callable=AsyncMock) as mock_parent_run:
            mock_parent_run.return_value = MagicMock(spec=AgentHistoryList)
            await agent.run(max_steps=50)
            mock_parent_run.assert_called_once_with(
                max_steps=50, on_step_start=None, on_step_end=None
            ), "Parent run should be called with max_steps=50"

    @pytest.mark.asyncio
    async def test_step_method_basic_flow(
        self,
        agent: ConcreteBugninjaAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test the basic step method execution flow, including hooks and state updates."""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()
        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100
        agent.get_next_action = AsyncMock(return_value=mock_agent_output)  # type: ignore[method-assign]
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])  # type: ignore[method-assign]
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]
        await agent.step()
        assert agent.before_step_called, "before_step_called should be True after step()"
        assert agent.after_step_called, "after_step_called should be True after step()"
        assert agent.state.n_steps == 1, "n_steps should increment to 1 after step()"
        assert (
            agent.state.consecutive_failures == 0
        ), "consecutive_failures should reset to 0 after step()"

    @pytest.mark.asyncio
    async def test_step_method_with_memory_enabled(
        self,
        agent: ConcreteBugninjaAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test step method when memory is enabled, ensuring procedural memory is created."""
        agent.enable_memory = True
        agent.memory = MagicMock()
        agent.memory.config.memory_interval = 1
        agent.state.n_steps = 0
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()
        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100
        agent.get_next_action = AsyncMock(return_value=mock_agent_output)  # type: ignore[method-assign]
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])  # type: ignore[method-assign]
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]
        await agent.step()
        agent.memory.create_procedural_memory.assert_called_once_with(
            1
        ), "create_procedural_memory should be called with interval 1"

    @pytest.mark.asyncio
    async def test_step_method_with_planner(
        self,
        agent: ConcreteBugninjaAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test step method when planner is configured, ensuring planner is called and plan is added."""
        agent.settings.planner_llm = MagicMock()
        agent.settings.planner_interval = 1
        agent.state.n_steps = 0
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()
        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100
        agent.get_next_action = AsyncMock(return_value=mock_agent_output)  # type: ignore[method-assign]
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])
        with patch.object(agent, "_run_planner", new_callable=AsyncMock) as mock_planner:
            mock_planner.return_value = "Test plan"
            mock_action = MagicMock()
            mock_action.model_dump.return_value = {"click": {"selector": "button"}}
            mock_agent_output.action = [mock_action]
            await agent.step()
            mock_planner.assert_called_once(), "Planner should be called once when planner is configured"
            agent._message_manager.add_plan.assert_called_once_with(
                "Test plan", position=-1
            ), "add_plan should be called with the generated plan"

    @pytest.mark.asyncio
    async def test_step_method_with_last_step_warning(
        self,
        agent: ConcreteBugninjaAgent,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test step method when it's the last step, ensuring last step warning is added."""
        step_info = MagicMock()
        step_info.is_last_step.return_value = True
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()
        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100
        agent.get_next_action = AsyncMock(return_value=mock_agent_output)  # type: ignore[method-assign]
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])  # type: ignore[method-assign]
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"done": {"success": True, "text": "Task completed"}}
        mock_agent_output.action = [mock_action]
        await agent.step(step_info)
        agent._message_manager._add_message_with_tokens.assert_called(), "Should add a message with tokens for last step warning"
        call_args = agent._message_manager._add_message_with_tokens.call_args[0][0]
        assert isinstance(call_args, HumanMessage), "Last step warning should be a HumanMessage"
        assert isinstance(call_args.content, str), "Last step warning content should be a string"
        assert (
            "last step" in call_args.content.lower()
        ), "Last step warning message should mention 'last step'"
