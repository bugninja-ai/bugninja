import asyncio
import time
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from browser_use.agent.views import (
    ActionResult,
    AgentBrain,
    AgentHistoryList,
    AgentOutput,
    StepMetadata,
)
from browser_use.browser.views import BrowserStateSummary
from browser_use.controller.registry.views import ActionModel
from langchain_core.messages import HumanMessage

from src.agents.bugninja_agent_base import BugninjaAgentBase, hook_missing_error


class ConcreteBugninjaAgent(BugninjaAgentBase):
    """Concrete implementation of BugninjaAgentBase for testing"""

    def __init__(self) -> None:
        self.before_step_called = False
        self.after_step_called = False
        self.before_run_called = False
        self.after_run_called = False
        self.before_action_called = False
        self.after_action_called = False
        self.hook_calls = []

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
        self.browser_profile = MagicMock()
        self.browser_profile.wait_between_actions = 0.1

        self.sensitive_data = {}
        self.context = {}
        self.tool_calling_method = "raw"

        # Mock action models
        self.ActionModel = MagicMock()
        self.DoneAgentOutput = MagicMock()

        # Mock callbacks
        self.register_new_step_callback = None

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

    async def get_next_action(self, messages: List) -> AgentOutput:
        # Mock implementation for testing
        return AgentOutput(action=[], current_state=AgentBrain(thought="Test thought"))


class TestBugninjaAgentBase:
    """Test suite for BugninjaAgentBase class"""

    @pytest.fixture
    def agent(self) -> None:
        """Create a concrete agent instance for testing"""
        return ConcreteBugninjaAgent()

    @pytest.fixture
    def mock_page(self) -> None:
        """Create a mock page"""
        page = MagicMock()
        page.wait_for_load_state = AsyncMock()
        page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
        return page

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
    def mock_action_model(self) -> None:
        """Create a mock action model"""
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None
        return action

    def test_hook_missing_error(self) -> None:
        """Test the hook_missing_error helper function"""
        error = hook_missing_error("test_hook", ConcreteBugninjaAgent)
        assert isinstance(error, NotImplementedError)
        assert "test_hook" in str(error)
        assert "ConcreteBugninjaAgent" in str(error)

    @pytest.mark.asyncio
    async def test_get_raw_html_of_playwright_page_success(self, agent, mock_page) -> None:
        """Test successful HTML extraction from Playwright page"""
        html_content = await agent.get_raw_html_of_playwright_page(mock_page)

        assert html_content == "<html><body>Test Content</body></html>"
        mock_page.wait_for_load_state.assert_has_calls([call("domcontentloaded"), call("load")])
        mock_page.content.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_raw_html_of_playwright_page_with_custom_content(self, agent) -> None:
        """Test HTML extraction with custom content"""
        custom_html = "<html><body><h1>Custom Content</h1></body></html>"
        page = MagicMock()
        page.wait_for_load_state = AsyncMock()
        page.content = AsyncMock(return_value=custom_html)

        html_content = await agent.get_raw_html_of_playwright_page(page)

        assert html_content == custom_html

    @pytest.mark.asyncio
    async def test_run_method_execution_flow(self, agent) -> None:
        """Test the complete run method execution flow"""
        # Mock the parent class run method
        with patch.object(BugninjaAgentBase, "run", new_callable=AsyncMock) as mock_parent_run:
            mock_parent_run.return_value = MagicMock(spec=AgentHistoryList)

            await agent.run(max_steps=10)

            # Verify hooks were called
            assert agent.before_run_called
            assert agent.after_run_called

            # Verify parent run was called with correct parameters
            mock_parent_run.assert_called_once_with(
                max_steps=10, on_step_start=None, on_step_end=None
            )

            # Verify hook call order
            assert agent.hook_calls[0][0] == "before_run"
            assert agent.hook_calls[-1][0] == "after_run"

    @pytest.mark.asyncio
    async def test_run_method_with_different_max_steps(self, agent) -> None:
        """Test run method with different max_steps values"""
        with patch.object(BugninjaAgentBase, "run", new_callable=AsyncMock) as mock_parent_run:
            mock_parent_run.return_value = MagicMock(spec=AgentHistoryList)

            await agent.run(max_steps=50)
            mock_parent_run.assert_called_once_with(
                max_steps=50, on_step_start=None, on_step_end=None
            )

    @pytest.mark.asyncio
    async def test_step_method_basic_flow(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test the basic step method execution flow"""
        # Mock all the dependencies
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        # Mock the action model
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        await agent.step()

        # Verify hooks were called
        assert agent.before_step_called
        assert agent.after_step_called

        # Verify state was updated
        assert agent.state.n_steps == 1
        assert agent.state.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_step_method_with_memory_enabled(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test step method when memory is enabled"""
        agent.enable_memory = True
        agent.memory = MagicMock()
        agent.memory.config.memory_interval = 1
        agent.state.n_steps = 0

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        await agent.step()

        # Verify memory was created
        agent.memory.create_procedural_memory.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_step_method_with_planner(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test step method when planner is configured"""
        agent.settings.planner_llm = MagicMock()
        agent.settings.planner_interval = 1
        agent.state.n_steps = 0

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        # Mock the planner
        with patch.object(agent, "_run_planner", new_callable=AsyncMock) as mock_planner:
            mock_planner.return_value = "Test plan"

            mock_action = MagicMock()
            mock_action.model_dump.return_value = {"click": {"selector": "button"}}
            mock_agent_output.action = [mock_action]

            await agent.step()

            # Verify planner was called
            mock_planner.assert_called_once()
            agent._message_manager.add_plan.assert_called_once_with("Test plan", position=-1)

    @pytest.mark.asyncio
    async def test_step_method_with_last_step_warning(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test step method when it's the last step"""
        # Create step info indicating last step
        step_info = MagicMock()
        step_info.is_last_step.return_value = True

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"done": {"success": True, "text": "Task completed"}}
        mock_agent_output.action = [mock_action]

        await agent.step(step_info)

        # Verify last step warning was added
        agent._message_manager._add_message_with_tokens.assert_called()
        call_args = agent._message_manager._add_message_with_tokens.call_args[0][0]
        assert isinstance(call_args, HumanMessage)
        assert "last step" in call_args.content.lower()

    @pytest.mark.asyncio
    async def test_step_method_with_empty_action_retry(
        self, agent, mock_browser_state_summary
    ) -> None:
        """Test step method when model returns empty action and retry is needed"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        # First call returns empty action, second call returns valid action
        empty_output = AgentOutput(action=[], current_state=AgentBrain(thought="Empty"))
        valid_output = AgentOutput(action=[MagicMock()], current_state=AgentBrain(thought="Valid"))

        agent.get_next_action = AsyncMock(side_effect=[empty_output, valid_output])
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        await agent.step()

        # Verify get_next_action was called twice
        assert agent.get_next_action.call_count == 2

    @pytest.mark.asyncio
    async def test_step_method_with_empty_action_after_retry(
        self, agent, mock_browser_state_summary
    ) -> None:
        """Test step method when model returns empty action even after retry"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        # Both calls return empty actions
        empty_output = AgentOutput(action=[], current_state=AgentBrain(thought="Empty"))
        agent.get_next_action = AsyncMock(return_value=empty_output)

        # Mock the action model creation
        mock_action = MagicMock()
        mock_action.model_dump.return_value = {
            "done": {"success": False, "text": "No next action returned by LLM!"}
        }
        agent.ActionModel.return_value = mock_action

        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        await agent.step()

        # Verify safe noop action was created
        agent.ActionModel.assert_called_once()

    @pytest.mark.asyncio
    async def test_step_method_with_conversation_saving(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test step method when conversation saving is enabled"""
        agent.settings.save_conversation_path = "/tmp/test_conversation"

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        with patch("src.agents.bugninja_agent_base.save_conversation") as mock_save:
            await agent.step()

            # Verify conversation was saved
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_step_method_with_cancellation(self, agent, mock_browser_state_summary) -> None:
        """Test step method when cancelled during execution"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        # Simulate cancellation during get_next_action
        agent.get_next_action = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(InterruptedError, match="Model query cancelled by user"):
            await agent.step()

    @pytest.mark.asyncio
    async def test_step_method_with_interruption(self, agent, mock_browser_state_summary) -> None:
        """Test step method when interrupted during execution"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        # Simulate interruption during get_next_action
        agent.get_next_action = AsyncMock(side_effect=InterruptedError("Agent paused"))

        with pytest.raises(InterruptedError, match="Agent paused"):
            await agent.step()

    @pytest.mark.asyncio
    async def test_step_method_with_exception(self, agent, mock_browser_state_summary) -> None:
        """Test step method when an exception occurs"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        # Simulate exception during get_next_action
        agent.get_next_action = AsyncMock(side_effect=Exception("Test error"))

        with patch.object(
            agent, "_handle_step_error", new_callable=AsyncMock
        ) as mock_error_handler:
            mock_error_handler.return_value = [ActionResult(error="Handled error")]

            await agent.step()

            # Verify error handler was called
            mock_error_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_act_basic_flow(self, agent, mock_action_model) -> None:
        """Test the basic multi_act method execution flow"""
        actions = [mock_action_model]

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        results = await agent.multi_act(actions)

        assert len(results) == 1
        assert results[0].extracted_content == "Success"
        agent.controller.act.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_act_multiple_actions(self, agent) -> None:
        """Test multi_act with multiple actions"""
        actions = [MagicMock(), MagicMock(), MagicMock()]
        for action in actions:
            action.model_dump.return_value = {"click": {"selector": "button"}}
            action.get_index.return_value = None

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        results = await agent.multi_act(actions)

        assert len(results) == 3
        assert agent.controller.act.call_count == 3

    @pytest.mark.asyncio
    async def test_multi_act_with_index_change_detection(self, agent) -> None:
        """Test multi_act with index change detection"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = "button_1"

        action2 = MagicMock()
        action2.model_dump.return_value = {"click": {"selector": "button"}}
        action2.get_index.return_value = "button_1"

        actions = [action1, action2]

        # Mock selector maps with different hashes
        original_selector_map = {
            "button_1": MagicMock(hash=MagicMock(branch_path_hash="original_hash"))
        }
        new_selector_map = {"button_1": MagicMock(hash=MagicMock(branch_path_hash="new_hash"))}

        agent.browser_session.get_selector_map = AsyncMock(
            side_effect=[original_selector_map, new_selector_map]
        )
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        results = await agent.multi_act(actions)

        # Should break after first action due to index change
        assert len(results) == 1
        assert "Element index changed" in results[0].extracted_content

    @pytest.mark.asyncio
    async def test_multi_act_with_new_elements_detection(self, agent) -> None:
        """Test multi_act with new elements detection"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = None

        action2 = MagicMock()
        action2.model_dump.return_value = {"click": {"selector": "button"}}
        action2.get_index.return_value = "button_1"

        actions = [action1, action2]

        # Mock selector maps with new elements
        original_selector_map = {"button_1": MagicMock(hash=MagicMock(branch_path_hash="hash1"))}
        new_selector_map = {
            "button_1": MagicMock(hash=MagicMock(branch_path_hash="hash1")),
            "button_2": MagicMock(hash=MagicMock(branch_path_hash="hash2")),
        }

        agent.browser_session.get_selector_map = AsyncMock(
            side_effect=[original_selector_map, new_selector_map]
        )
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        results = await agent.multi_act(actions, check_for_new_elements=True)

        # Should break after first action due to new elements
        assert len(results) == 1
        assert "Something new appeared" in results[0].extracted_content

    @pytest.mark.asyncio
    async def test_multi_act_with_action_cancellation(self, agent) -> None:
        """Test multi_act when an action is cancelled"""
        action = MagicMock()
        action.model_dump.return_value = {"click": {"selector": "button"}}
        action.get_index.return_value = None

        actions = [action]

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(InterruptedError, match="Action cancelled by user"):
            await agent.multi_act(actions)

    @pytest.mark.asyncio
    async def test_multi_act_with_done_action(self, agent) -> None:
        """Test multi_act stops when done action is encountered"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = None

        action2 = MagicMock()
        action2.model_dump.return_value = {"done": {"success": True, "text": "Task completed"}}
        action2.get_index.return_value = None

        actions = [action1, action2]

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()

        # First action succeeds, second action is done
        agent.controller.act = AsyncMock(
            side_effect=[
                ActionResult(extracted_content="Success"),
                ActionResult(extracted_content="Done", is_done=True),
            ]
        )

        results = await agent.multi_act(actions)

        # Should stop after done action
        assert len(results) == 2
        assert results[1].is_done

    @pytest.mark.asyncio
    async def test_multi_act_with_error_action(self, agent) -> None:
        """Test multi_act stops when error action is encountered"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = None

        action2 = MagicMock()
        action2.model_dump.return_value = {"click": {"selector": "button"}}
        action2.get_index.return_value = None

        actions = [action1, action2]

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()

        # First action succeeds, second action has error
        agent.controller.act = AsyncMock(
            side_effect=[
                ActionResult(extracted_content="Success"),
                ActionResult(error="Action failed"),
            ]
        )

        results = await agent.multi_act(actions)

        # Should stop after error action
        assert len(results) == 2
        assert results[1].error == "Action failed"

    @pytest.mark.asyncio
    async def test_multi_act_with_wait_between_actions(self, agent) -> None:
        """Test multi_act respects wait_between_actions setting"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = None

        action2 = MagicMock()
        action2.model_dump.return_value = {"click": {"selector": "button"}}
        action2.get_index.return_value = None

        actions = [action1, action2]

        agent.browser_session.get_selector_map = AsyncMock(return_value={})
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        start_time = time.time()
        results = await agent.multi_act(actions)
        end_time = time.time()

        # Should have waited between actions
        assert len(results) == 2
        assert end_time - start_time >= agent.browser_profile.wait_between_actions

    @pytest.mark.asyncio
    async def test_multi_act_without_checking_new_elements(self, agent) -> None:
        """Test multi_act when check_for_new_elements is False"""
        action1 = MagicMock()
        action1.model_dump.return_value = {"click": {"selector": "button"}}
        action1.get_index.return_value = None

        action2 = MagicMock()
        action2.model_dump.return_value = {"click": {"selector": "button"}}
        action2.get_index.return_value = "button_1"

        actions = [action1, action2]

        # Mock selector maps with new elements
        original_selector_map = {"button_1": MagicMock(hash=MagicMock(branch_path_hash="hash1"))}
        new_selector_map = {
            "button_1": MagicMock(hash=MagicMock(branch_path_hash="hash1")),
            "button_2": MagicMock(hash=MagicMock(branch_path_hash="hash2")),
        }

        agent.browser_session.get_selector_map = AsyncMock(
            side_effect=[original_selector_map, new_selector_map]
        )
        agent.browser_session.remove_highlights = AsyncMock()
        agent.controller.act = AsyncMock(return_value=ActionResult(extracted_content="Success"))

        results = await agent.multi_act(actions, check_for_new_elements=False)

        # Should not break due to new elements when check_for_new_elements is False
        assert len(results) == 2

    def test_abstract_methods_not_implemented(self) -> None:
        """Test that abstract methods raise NotImplementedError when not implemented"""

        # Create a class that doesn't implement the abstract methods
        class IncompleteAgent(BugninjaAgentBase):
            pass

        agent = IncompleteAgent()

        # Test that each abstract method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            asyncio.run(agent._before_step_hook(MagicMock(), MagicMock()))

        with pytest.raises(NotImplementedError):
            asyncio.run(agent._after_step_hook(MagicMock(), MagicMock()))

        with pytest.raises(NotImplementedError):
            asyncio.run(agent._before_run_hook())

        with pytest.raises(NotImplementedError):
            asyncio.run(agent._after_run_hook())

        with pytest.raises(NotImplementedError):
            asyncio.run(agent._before_action_hook(MagicMock()))

        with pytest.raises(NotImplementedError):
            asyncio.run(agent._after_action_hook(MagicMock()))

    @pytest.mark.asyncio
    async def test_hook_execution_order(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test that hooks are executed in the correct order"""
        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        await agent.step()

        # Verify hook execution order
        expected_order = ["before_step", "before_action", "after_action", "after_step"]
        actual_order = [call[0] for call in agent.hook_calls if call[0] in expected_order]
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_register_new_step_callback(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test that register_new_step_callback is called when provided"""
        callback_called = False
        callback_data = None

        def test_callback(browser_state, model_output, step_number) -> None:
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = (browser_state, model_output, step_number)

        agent.register_new_step_callback = test_callback

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        await agent.step()

        # Verify callback was called
        assert callback_called
        assert callback_data[0] == mock_browser_state_summary
        assert callback_data[1] == mock_agent_output
        assert callback_data[2] == 1

    @pytest.mark.asyncio
    async def test_register_new_step_callback_async(
        self, agent, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test that async register_new_step_callback is called when provided"""
        callback_called = False
        callback_data = None

        async def test_async_callback(browser_state, model_output, step_number) -> None:
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = (browser_state, model_output, step_number)

        agent.register_new_step_callback = test_async_callback

        agent.browser_session.get_state_summary = AsyncMock(return_value=mock_browser_state_summary)
        agent.browser_session.get_current_page = AsyncMock()
        agent.browser_session.remove_highlights = AsyncMock()

        agent._message_manager.get_messages.return_value = []
        agent._message_manager.state.history.current_tokens = 100

        agent.get_next_action = AsyncMock(return_value=mock_agent_output)
        agent.multi_act = AsyncMock(return_value=[ActionResult(extracted_content="Success")])

        mock_action = MagicMock()
        mock_action.model_dump.return_value = {"click": {"selector": "button"}}
        mock_agent_output.action = [mock_action]

        await agent.step()

        # Verify async callback was called
        assert callback_called
        assert callback_data[0] == mock_browser_state_summary
        assert callback_data[1] == mock_agent_output
        assert callback_data[2] == 1
