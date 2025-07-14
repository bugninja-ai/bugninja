from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from browser_use.agent.views import ActionResult, AgentOutput, DOMElementNode
from browser_use.browser.session import Page
from browser_use.browser.views import BrowserStateSummary
from browser_use.controller.views import ScrollAction
from pydantic import BaseModel

from src.agents.extensions import (
    ALTERNATIVE_XPATH_SELECTORS_KEY,
    DOM_ELEMENT_DATA_KEY,
    SELECTOR_ORIENTED_ACTIONS,
    BugninjaController,
    extend_agent_action_with_info,
)
from src.schemas.pipeline import BugninjaExtendedAction
from src.utils.selector_factory import SelectorFactory


class TestExtensions:
    """Test suite for extensions module"""

    @pytest.fixture
    def mock_page(self) -> None:
        """Create a mock page"""
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
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
        return AgentOutput(action=[], current_state=MagicMock())

    @pytest.fixture
    def mock_dom_element_node(self) -> None:
        """Create a mock DOM element node"""
        element = MagicMock(spec=DOMElementNode)
        element.__json__.return_value = {
            "tag_name": "button",
            "attributes": {"id": "test-button", "class": "btn-primary"},
            "xpath": "/html/body/div/button[@id='test-button']",
            "text_content": "Click me",
            "is_visible": True,
            "is_enabled": True,
        }
        return element

    @pytest.fixture
    def mock_action_model(self) -> None:
        """Create a mock action model for selector-oriented action"""
        action = MagicMock()
        action.model_dump.return_value = {
            "click_element_by_index": {"index": 0, "text": "Click the button"}
        }
        return action

    @pytest.fixture
    def mock_non_selector_action_model(self) -> None:
        """Create a mock action model for non-selector-oriented action"""
        action = MagicMock()
        action.model_dump.return_value = {"goto": {"url": "https://example.com"}}
        return action

    @pytest.fixture
    def bugninja_controller(self) -> None:
        """Create a BugninjaController instance for testing"""
        return BugninjaController(verbose=True)

    @pytest.fixture
    def mock_browser_session(self) -> None:
        """Create a mock browser session"""
        session = MagicMock()
        session.get_current_page = AsyncMock()
        return session

    def test_selector_oriented_actions_constant(self) -> None:
        """Test that SELECTOR_ORIENTED_ACTIONS contains expected actions"""
        expected_actions = [
            "click_element_by_index",
            "input_text",
            "get_dropdown_options",
            "select_dropdown_option",
            "drag_drop",
        ]

        assert SELECTOR_ORIENTED_ACTIONS == expected_actions
        assert len(SELECTOR_ORIENTED_ACTIONS) == 5

    def test_constants_values(self) -> None:
        """Test that constants have expected values"""
        assert ALTERNATIVE_XPATH_SELECTORS_KEY == "alternative_relative_xpaths"
        assert DOM_ELEMENT_DATA_KEY == "dom_element_data"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_selector_oriented_action(
        self,
        mock_page,
        mock_browser_state_summary,
        mock_agent_output,
        mock_action_model,
        mock_dom_element_node,
    ) -> None:
        """Test extending selector-oriented actions with DOM element data"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model]
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Mock HTML content
        mock_html = "<html><body><button id='test-button'>Click me</button></body></html>"

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.return_value = [
                    "//button[@id='test-button']",
                    "//div/button",
                    "//button[contains(text(), 'Click')]",
                ]
                mock_factory_class.return_value = mock_factory

                # Execute function
                result = await extend_agent_action_with_info(
                    brain_state_id=brain_state_id,
                    current_page=mock_page,
                    model_output=mock_agent_output,
                    browser_state_summary=mock_browser_state_summary,
                )

                # Verify results
                assert len(result) == 1
                extended_action = result[0]

                # Verify basic structure
                assert extended_action.brain_state_id == brain_state_id
                assert extended_action.action == mock_action_model.model_dump()

                # Verify DOM element data was added
                assert extended_action.dom_element_data is not None
                dom_data = extended_action.dom_element_data

                # Verify DOM element data structure
                assert dom_data["tag_name"] == "button"
                assert dom_data["attributes"]["id"] == "test-button"
                assert dom_data["xpath"] == "/html/body/div/button[@id='test-button']"

                # Verify alternative XPath selectors were generated
                assert ALTERNATIVE_XPATH_SELECTORS_KEY in dom_data
                alternative_selectors = dom_data[ALTERNATIVE_XPATH_SELECTORS_KEY]
                assert len(alternative_selectors) == 3
                assert "//button[@id='test-button']" in alternative_selectors

                # Verify HTML was retrieved
                mock_get_html.assert_called_once_with(page=mock_page)

                # Verify SelectorFactory was used
                mock_factory_class.assert_called_once_with(mock_html)
                mock_factory.generate_relative_xpaths_from_full_xpath.assert_called_once_with(
                    full_xpath="//html/body/div/button[@id='test-button']"
                )

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_non_selector_action(
        self,
        mock_page,
        mock_browser_state_summary,
        mock_agent_output,
        mock_non_selector_action_model,
    ) -> None:
        """Test extending non-selector-oriented actions (should not add DOM element data)"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_non_selector_action_model]

        # Execute function
        result = await extend_agent_action_with_info(
            brain_state_id=brain_state_id,
            current_page=mock_page,
            model_output=mock_agent_output,
            browser_state_summary=mock_browser_state_summary,
        )

        # Verify results
        assert len(result) == 1
        extended_action = result[0]

        # Verify basic structure
        assert extended_action.brain_state_id == brain_state_id
        assert extended_action.action == mock_non_selector_action_model.model_dump()

        # Verify no DOM element data was added
        assert extended_action.dom_element_data is None

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_multiple_actions(
        self,
        mock_page,
        mock_browser_state_summary,
        mock_agent_output,
        mock_action_model,
        mock_non_selector_action_model,
        mock_dom_element_node,
    ) -> None:
        """Test extending multiple actions of different types"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model, mock_non_selector_action_model]
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Mock HTML content
        mock_html = "<html><body><button id='test-button'>Click me</button></body></html>"

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.return_value = ["//button"]
                mock_factory_class.return_value = mock_factory

                # Execute function
                result = await extend_agent_action_with_info(
                    brain_state_id=brain_state_id,
                    current_page=mock_page,
                    model_output=mock_agent_output,
                    browser_state_summary=mock_browser_state_summary,
                )

                # Verify results
                assert len(result) == 2

                # First action (selector-oriented) should have DOM element data
                assert result[0].dom_element_data is not None
                assert result[0].action == mock_action_model.model_dump()

                # Second action (non-selector-oriented) should not have DOM element data
                assert result[1].dom_element_data is None
                assert result[1].action == mock_non_selector_action_model.model_dump()

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_selector_factory_error(
        self,
        mock_page,
        mock_browser_state_summary,
        mock_agent_output,
        mock_action_model,
        mock_dom_element_node,
    ) -> None:
        """Test handling of SelectorFactory errors"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model]
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Mock HTML content
        mock_html = "<html><body><button id='test-button'>Click me</button></body></html>"

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory to raise an exception
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.side_effect = Exception(
                    "Selector generation failed"
                )
                mock_factory_class.return_value = mock_factory

                # Execute function (should not raise exception)
                result = await extend_agent_action_with_info(
                    brain_state_id=brain_state_id,
                    current_page=mock_page,
                    model_output=mock_agent_output,
                    browser_state_summary=mock_browser_state_summary,
                )

                # Verify results
                assert len(result) == 1
                extended_action = result[0]

                # Verify DOM element data was still added
                assert extended_action.dom_element_data is not None

                # Verify alternative selectors are None due to error
                dom_data = extended_action.dom_element_data
                assert dom_data[ALTERNATIVE_XPATH_SELECTORS_KEY] is None

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_missing_index(
        self, mock_page, mock_browser_state_summary, mock_agent_output
    ) -> None:
        """Test handling of actions with missing index"""
        # Create action without index
        action = MagicMock()
        action.model_dump.return_value = {
            "click_element_by_index": {
                "text": "Click the button"
                # Missing index
            }
        }
        mock_agent_output.action = [action]

        # Execute function (should handle gracefully)
        result = await extend_agent_action_with_info(
            brain_state_id="test_brain_id",
            current_page=mock_page,
            model_output=mock_agent_output,
            browser_state_summary=mock_browser_state_summary,
        )

        # Should still return the action
        assert len(result) == 1
        assert result[0].action == action.model_dump()

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_empty_actions(
        self, mock_page, mock_browser_state_summary
    ) -> None:
        """Test extending empty action list"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output = AgentOutput(action=[], current_state=MagicMock())

        # Execute function
        result = await extend_agent_action_with_info(
            brain_state_id=brain_state_id,
            current_page=mock_page,
            model_output=mock_agent_output,
            browser_state_summary=mock_browser_state_summary,
        )

        # Verify empty result
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_xpath_formatting(
        self,
        mock_page,
        mock_browser_state_summary,
        mock_agent_output,
        mock_action_model,
        mock_dom_element_node,
    ) -> None:
        """Test that XPath is properly formatted"""
        # Setup with different XPath formats
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model]
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Modify the XPath to test formatting
        mock_dom_element_node.__json__.return_value = {
            "tag_name": "button",
            "attributes": {"id": "test-button"},
            "xpath": "html/body/div/button[@id='test-button']",  # Without leading //
            "text_content": "Click me",
            "is_visible": True,
            "is_enabled": True,
        }

        # Mock HTML content
        mock_html = "<html><body><button id='test-button'>Click me</button></body></html>"

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.return_value = ["//button"]
                mock_factory_class.return_value = mock_factory

                # Execute function
                result = await extend_agent_action_with_info(
                    brain_state_id=brain_state_id,
                    current_page=mock_page,
                    model_output=mock_agent_output,
                    browser_state_summary=mock_browser_state_summary,
                )

                # Verify XPath was properly formatted
                assert len(result) == 1
                dom_data = result[0].dom_element_data

                # Verify the XPath was formatted correctly
                expected_xpath = "//html/body/div/button[@id='test-button']"
                assert dom_data["xpath"] == expected_xpath

                # Verify SelectorFactory was called with formatted XPath
                mock_factory.generate_relative_xpaths_from_full_xpath.assert_called_once_with(
                    full_xpath=expected_xpath
                )

    def test_bugninja_controller_initialization(self, bugninja_controller) -> None:
        """Test BugninjaController initialization"""
        assert isinstance(bugninja_controller, BugninjaController)
        assert bugninja_controller.verbose is True

    def test_bugninja_controller_with_exclude_actions(self) -> None:
        """Test BugninjaController initialization with exclude_actions"""
        exclude_actions = ["scroll_up", "scroll_down"]
        controller = BugninjaController(exclude_actions=exclude_actions, verbose=False)

        assert controller.verbose is False
        # Note: We can't easily test exclude_actions without accessing internal registry

    def test_bugninja_controller_with_output_model(self) -> None:
        """Test BugninjaController initialization with output_model"""

        class TestModel(BaseModel):
            test_field: str

        controller = BugninjaController(output_model=TestModel, verbose=True)
        assert controller.verbose is True

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_down_action(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test scroll_down action"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(return_value=800)  # page height
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.mouse.wheel = AsyncMock()

        scroll_action = ScrollAction(amount=500)

        # Execute scroll_down action
        result = await bugninja_controller.scroll_down(scroll_action, mock_browser_session)

        # Verify results
        assert isinstance(result, ActionResult)
        assert "Scrolled down the page by 500 pixels" in result.extracted_content
        assert result.include_in_memory is True

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.wait_for_load_state.assert_called_once_with("load")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=500)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_up_action(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test scroll_up action"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(return_value=800)  # page height
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.mouse.wheel = AsyncMock()

        scroll_action = ScrollAction(amount=300)

        # Execute scroll_up action
        result = await bugninja_controller.scroll_up(scroll_action, mock_browser_session)

        # Verify results
        assert isinstance(result, ActionResult)
        assert "Scrolled down the page by -300 pixels" in result.extracted_content
        assert result.include_in_memory is True

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.wait_for_load_state.assert_called_once_with("load")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=-300)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_without_amount(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test scroll actions without specifying amount (should use page height)"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(return_value=1000)  # page height
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.mouse.wheel = AsyncMock()

        scroll_action = ScrollAction(amount=None)  # No amount specified

        # Execute scroll_down action
        result = await bugninja_controller.scroll_down(scroll_action, mock_browser_session)

        # Verify results
        assert isinstance(result, ActionResult)
        assert "Scrolled down the page by 1000 pixels" in result.extracted_content

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=1000)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_up_without_amount(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test scroll_up action without specifying amount"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(return_value=1000)  # page height
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.mouse.wheel = AsyncMock()

        scroll_action = ScrollAction(amount=None)  # No amount specified

        # Execute scroll_up action
        result = await bugninja_controller.scroll_up(scroll_action, mock_browser_session)

        # Verify results
        assert isinstance(result, ActionResult)
        assert "Scrolled down the page by -1000 pixels" in result.extracted_content

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=-1000)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_error_handling(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test error handling in scroll actions"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(side_effect=Exception("Page evaluation failed"))

        scroll_action = ScrollAction(amount=100)

        # Execute scroll action (should raise exception)
        with pytest.raises(Exception, match="Page evaluation failed"):
            await bugninja_controller.scroll_down(scroll_action, mock_browser_session)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_mouse_wheel_error(
        self, bugninja_controller, mock_browser_session
    ) -> None:
        """Test error handling when mouse.wheel fails"""
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)
        mock_page.evaluate = AsyncMock(return_value=800)
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.mouse.wheel = AsyncMock(side_effect=Exception("Mouse wheel failed"))

        scroll_action = ScrollAction(amount=100)

        # Execute scroll action (should raise exception)
        with pytest.raises(Exception, match="Mouse wheel failed"):
            await bugninja_controller.scroll_down(scroll_action, mock_browser_session)

    def test_bugninja_controller_registry_actions(self, bugninja_controller) -> None:
        """Test that scroll actions are properly registered"""
        # Verify that the actions are available in the registry
        # This is a basic test - in practice, you might need to access the registry directly
        assert hasattr(bugninja_controller, "scroll_down")
        assert hasattr(bugninja_controller, "scroll_up")
        assert callable(bugninja_controller.scroll_down)
        assert callable(bugninja_controller.scroll_up)

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_all_selector_actions(
        self, mock_page, mock_browser_state_summary, mock_agent_output, mock_dom_element_node
    ) -> None:
        """Test extending all selector-oriented actions"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Mock HTML content
        mock_html = "<html><body><button id='test-button'>Click me</button></body></html>"

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.return_value = ["//button"]
                mock_factory_class.return_value = mock_factory

                # Test each selector-oriented action
                for action_type in SELECTOR_ORIENTED_ACTIONS:
                    # Create action for this type
                    action = MagicMock()
                    action.model_dump.return_value = {
                        action_type: {"index": 0, "text": f"Test {action_type}"}
                    }
                    mock_agent_output.action = [action]

                    # Execute function
                    result = await extend_agent_action_with_info(
                        brain_state_id=brain_state_id,
                        current_page=mock_page,
                        model_output=mock_agent_output,
                        browser_state_summary=mock_browser_state_summary,
                    )

                    # Verify results
                    assert len(result) == 1
                    extended_action = result[0]

                    # Verify DOM element data was added for all selector-oriented actions
                    assert extended_action.dom_element_data is not None
                    assert extended_action.brain_state_id == brain_state_id
                    assert extended_action.action == action.model_dump()

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_missing_selector_map_entry(
        self, mock_page, mock_browser_state_summary, mock_agent_output, mock_action_model
    ) -> None:
        """Test handling when selector_map doesn't contain the required index"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model]
        mock_browser_state_summary.selector_map = {}  # Empty selector map

        # Execute function (should handle gracefully)
        result = await extend_agent_action_with_info(
            brain_state_id=brain_state_id,
            current_page=mock_page,
            model_output=mock_agent_output,
            browser_state_summary=mock_browser_state_summary,
        )

        # Should still return the action
        assert len(result) == 1
        assert result[0].action == mock_action_model.model_dump()
        # DOM element data should be None since index wasn't found
        assert result[0].dom_element_data is None

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_complex_action_structure(
        self, mock_page, mock_browser_state_summary, mock_agent_output, mock_dom_element_node
    ) -> None:
        """Test extending actions with complex nested structures"""
        # Setup
        brain_state_id = "test_brain_id"
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Create complex action
        action = MagicMock()
        action.model_dump.return_value = {
            "drag_drop": {
                "index": 0,
                "target_index": 1,
                "text": "Drag and drop operation",
                "options": {"timeout": 5000, "force": True},
            }
        }
        mock_agent_output.action = [action]

        # Mock HTML content
        mock_html = (
            "<html><body><div id='source'>Source</div><div id='target'>Target</div></body></html>"
        )

        with patch(
            "src.agents.extensions.BugninjaAgentBase.get_raw_html_of_playwright_page",
            new_callable=AsyncMock,
        ) as mock_get_html:
            mock_get_html.return_value = mock_html

            # Mock SelectorFactory
            with patch("src.agents.extensions.SelectorFactory") as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory.generate_relative_xpaths_from_full_xpath.return_value = [
                    "//div[@id='source']"
                ]
                mock_factory_class.return_value = mock_factory

                # Execute function
                result = await extend_agent_action_with_info(
                    brain_state_id=brain_state_id,
                    current_page=mock_page,
                    model_output=mock_agent_output,
                    browser_state_summary=mock_browser_state_summary,
                )

                # Verify results
                assert len(result) == 1
                extended_action = result[0]

                # Verify complex action structure was preserved
                assert extended_action.action == action.model_dump()
                assert extended_action.action["drag_drop"]["index"] == 0
                assert extended_action.action["drag_drop"]["target_index"] == 1
                assert extended_action.action["drag_drop"]["options"]["timeout"] == 5000

                # Verify DOM element data was added
                assert extended_action.dom_element_data is not None
