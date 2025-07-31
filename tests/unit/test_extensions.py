from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import (  # type: ignore
    ActionResult,
    AgentBrain,
    AgentOutput,
    DOMElementNode,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from pydantic import BaseModel

from src.agents import (
    ALTERNATIVE_XPATH_SELECTORS_KEY,
    DOM_ELEMENT_DATA_KEY,
    SELECTOR_ORIENTED_ACTIONS,
    BugninjaController,
    extend_agent_action_with_info,
)


class TestExtensions:
    """Test suite for extensions module functionality.

    This test suite validates the core functionality of the extensions module,
    including DOM element data enrichment, action processing, and controller
    behavior. These tests ensure reliable action processing and proper error
    handling for browser automation scenarios.
    """

    @pytest.fixture
    def mock_page(self) -> Page:
        """Create a mock page for testing browser interactions.

        Returns:
            Page: A mock page object with basic URL and title properties.
        """
        page = MagicMock(spec=Page)
        page.url = "https://example.com"
        page.title = "Test Page"
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
        """Create a mock agent output for testing action processing.

        Returns:
            AgentOutput: A mock agent output with empty action list and
            mock current state for testing action extension functionality.
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
    def mock_dom_element_node(self) -> DOMElementNode:
        """Create a mock DOM element node for testing element data extraction.

        Returns:
            DOMElementNode: A mock DOM element representing a button with
            attributes, XPath, and visibility properties for testing DOM
            element data enrichment.
        """
        element = MagicMock(spec=DOMElementNode)
        element.__json__.return_value = {  # type: ignore[method-assign]
            "tag_name": "button",
            "attributes": {"id": "test-button", "class": "btn-primary"},
            "xpath": "/html/body/div/button[@id='test-button']",
            "text_content": "Click me",
            "is_visible": True,
            "is_enabled": True,
        }
        return element

    @pytest.fixture
    def mock_action_model(self) -> ActionModel:
        """Create a mock action model for selector-oriented action testing.

        Returns:
            ActionModel: A mock action model representing a click_element_by_index
            action with index and text properties for testing selector-oriented
            action processing.
        """
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {  # type: ignore[method-assign]
            "click_element_by_index": {"index": 0, "text": "Click the button"}
        }
        return action

    @pytest.fixture
    def mock_non_selector_action_model(self) -> ActionModel:
        """Create a mock action model for non-selector-oriented action testing.

        Returns:
            ActionModel: A mock action model representing a goto action with
            URL property for testing non-selector action processing.
        """
        action = MagicMock(spec=ActionModel)
        action.model_dump.return_value = {"goto": {"url": "https://example.com"}}  # type: ignore[method-assign]
        return action

    @pytest.fixture
    def bugninja_controller(self) -> BugninjaController:
        """Create a BugninjaController instance for testing controller functionality.

        Returns:
            BugninjaController: A controller instance with verbose logging enabled
            for testing scroll actions and controller behavior.
        """
        return BugninjaController(verbose=True)

    @pytest.fixture
    def mock_browser_session(self) -> BrowserSession:
        """Create a mock browser session for testing controller interactions.

        Returns:
            BrowserSession: A mock browser session with async get_current_page
            method for testing controller action execution.
        """
        session = MagicMock(spec=BrowserSession)
        session.get_current_page = AsyncMock()  # type: ignore[method-assign]
        return session

    def test_selector_oriented_actions_constant(self) -> None:
        """Test that SELECTOR_ORIENTED_ACTIONS contains expected actions.

        This test validates that the SELECTOR_ORIENTED_ACTIONS constant contains
        all the expected action types that require DOM element data enrichment.
        This is critical for ensuring that the correct actions are processed
        with additional DOM information for reliable browser automation.
        """
        expected_actions = [
            "click_element_by_index",
            "input_text",
            "get_dropdown_options",
            "select_dropdown_option",
            "drag_drop",
        ]

        assert SELECTOR_ORIENTED_ACTIONS == expected_actions, (
            f"Expected SELECTOR_ORIENTED_ACTIONS to contain {expected_actions}, "
            f"but got {SELECTOR_ORIENTED_ACTIONS}"
        )
        assert len(SELECTOR_ORIENTED_ACTIONS) == 5, (
            f"Expected SELECTOR_ORIENTED_ACTIONS to have 5 items, "
            f"but got {len(SELECTOR_ORIENTED_ACTIONS)}"
        )

    def test_constants_values(self) -> None:
        """Test that constants have expected values for DOM element processing.

        This test validates that the key constants used for DOM element data
        enrichment have the correct string values. These constants are used
        throughout the codebase for consistent DOM element data handling.
        """
        assert ALTERNATIVE_XPATH_SELECTORS_KEY == "alternative_relative_xpaths", (
            f"Expected ALTERNATIVE_XPATH_SELECTORS_KEY to be 'alternative_relative_xpaths', "
            f"but got '{ALTERNATIVE_XPATH_SELECTORS_KEY}'"
        )
        assert DOM_ELEMENT_DATA_KEY == "dom_element_data", (
            f"Expected DOM_ELEMENT_DATA_KEY to be 'dom_element_data', "
            f"but got '{DOM_ELEMENT_DATA_KEY}'"
        )

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_selector_oriented_action(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_action_model: ActionModel,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test extending selector-oriented actions with DOM element data.

        This test validates that selector-oriented actions are properly enriched
        with DOM element data including tag name, attributes, XPath, and alternative
        selectors. This enrichment is critical for reliable element identification
        and action execution in browser automation scenarios.
        """
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
                assert len(result) == 1, f"Expected 1 extended action, but got {len(result)}"
                extended_action = result[0]

                # Verify basic structure
                assert extended_action.brain_state_id == brain_state_id, (
                    f"Expected brain_state_id to be '{brain_state_id}', "
                    f"but got '{extended_action.brain_state_id}'"
                )
                assert (
                    extended_action.action == mock_action_model.model_dump()
                ), "Expected action to match original action model dump"

                # Verify DOM element data was added
                assert (
                    extended_action.dom_element_data is not None
                ), "Expected DOM element data to be added for selector-oriented action"
                dom_data = extended_action.dom_element_data

                # Verify DOM element data structure
                assert (
                    dom_data["tag_name"] == "button"
                ), f"Expected tag_name to be 'button', but got '{dom_data['tag_name']}'"
                assert (
                    dom_data["attributes"]["id"] == "test-button"
                ), f"Expected id attribute to be 'test-button', but got '{dom_data['attributes']['id']}'"
                assert (
                    dom_data["xpath"] == "/html/body/div/button[@id='test-button']"
                ), f"Expected xpath to match original, but got '{dom_data['xpath']}'"

                # Verify alternative XPath selectors were generated
                assert (
                    ALTERNATIVE_XPATH_SELECTORS_KEY in dom_data
                ), f"Expected '{ALTERNATIVE_XPATH_SELECTORS_KEY}' key in DOM element data"
                alternative_selectors = dom_data[ALTERNATIVE_XPATH_SELECTORS_KEY]
                assert (
                    len(alternative_selectors) == 3
                ), f"Expected 3 alternative selectors, but got {len(alternative_selectors)}"
                assert (
                    "//button[@id='test-button']" in alternative_selectors
                ), "Expected specific alternative selector to be present"

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
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_non_selector_action_model: ActionModel,
    ) -> None:
        """Test extending non-selector-oriented actions (should not add DOM element data).

        This test validates that non-selector actions like navigation actions
        are not enriched with DOM element data since they don't interact with
        specific page elements. This ensures that only relevant actions receive
        DOM enrichment for optimal performance and clarity.
        """
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
        assert len(result) == 1, f"Expected 1 extended action, but got {len(result)}"
        extended_action = result[0]

        # Verify basic structure
        assert extended_action.brain_state_id == brain_state_id, (
            f"Expected brain_state_id to be '{brain_state_id}', "
            f"but got '{extended_action.brain_state_id}'"
        )
        assert (
            extended_action.action == mock_non_selector_action_model.model_dump()
        ), "Expected action to match original action model dump"

        # Verify no DOM element data was added
        assert (
            extended_action.dom_element_data is None
        ), "Expected no DOM element data for non-selector-oriented action"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_multiple_actions(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_action_model: ActionModel,
        mock_non_selector_action_model: ActionModel,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test extending multiple actions of different types.

        This test validates that the function correctly processes mixed action
        lists containing both selector-oriented and non-selector actions.
        This is critical for ensuring that complex action sequences are
        properly handled with appropriate DOM enrichment for each action type.
        """
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
                assert len(result) == 2, f"Expected 2 extended actions, but got {len(result)}"

                # First action (selector-oriented) should have DOM element data
                assert (
                    result[0].dom_element_data is not None
                ), "Expected first action to have DOM element data"
                assert (
                    result[0].action == mock_action_model.model_dump()
                ), "Expected first action to match selector action model"

                # Second action (non-selector-oriented) should not have DOM element data
                assert (
                    result[1].dom_element_data is None
                ), "Expected second action to have no DOM element data"
                assert (
                    result[1].action == mock_non_selector_action_model.model_dump()
                ), "Expected second action to match non-selector action model"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_selector_factory_error(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_action_model: ActionModel,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test handling of SelectorFactory errors during DOM element processing.

        This test validates that the function gracefully handles SelectorFactory
        errors by continuing to process the action without alternative selectors.
        This error handling is critical for maintaining system stability when
        external selector generation services fail.
        """
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
                assert len(result) == 1, f"Expected 1 extended action, but got {len(result)}"
                extended_action = result[0]

                # Verify DOM element data was still added
                assert (
                    extended_action.dom_element_data is not None
                ), "Expected DOM element data to be added despite SelectorFactory error"

                # Verify alternative selectors are None due to error
                dom_data = extended_action.dom_element_data
                assert (
                    dom_data[ALTERNATIVE_XPATH_SELECTORS_KEY] is None
                ), "Expected alternative selectors to be None due to SelectorFactory error"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_missing_index(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test handling of actions with missing index in selector-oriented actions.

        This test validates that the function gracefully handles malformed
        selector-oriented actions that lack the required index parameter.
        This error handling ensures system stability when processing incomplete
        or corrupted action data from external sources.
        """
        # Create action without index
        action = MagicMock()
        action.model_dump.return_value = {  # type: ignore[method-assign]
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
        assert len(result) == 1, f"Expected 1 action to be returned, but got {len(result)}"
        assert (
            result[0].action == action.model_dump()
        ), "Expected returned action to match original action model"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_empty_actions(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
    ) -> None:
        """Test extending empty action list.

        This test validates that the function correctly handles empty action
        lists by returning an empty result. This edge case handling ensures
        that the function doesn't crash when processing agent outputs with
        no actions to extend.
        """
        # Setup
        brain_state_id = "test_brain_id"

        # Execute function
        result = await extend_agent_action_with_info(
            brain_state_id=brain_state_id,
            current_page=mock_page,
            model_output=mock_agent_output,
            browser_state_summary=mock_browser_state_summary,
        )

        # Verify empty result
        assert (
            len(result) == 0
        ), f"Expected empty result for empty actions, but got {len(result)} items"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_xpath_formatting(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_action_model: ActionModel,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test that XPath is properly formatted for selector generation.

        This test validates that XPath strings are correctly formatted with
        leading slashes before being passed to the SelectorFactory. This
        formatting is critical for ensuring that relative XPath generation
        works correctly with various XPath input formats.
        """
        # Setup with different XPath formats
        brain_state_id = "test_brain_id"
        mock_agent_output.action = [mock_action_model]
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Modify the XPath to test formatting
        mock_dom_element_node.__json__.return_value = {  # type: ignore[method-assign]
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
                assert len(result) == 1, f"Expected 1 extended action, but got {len(result)}"
                dom_data = result[0].dom_element_data

                # Verify the XPath was formatted correctly
                expected_xpath = "//html/body/div/button[@id='test-button']"
                assert dom_data is not None, "Expected DOM element data to be present"
                assert (
                    dom_data["xpath"] == expected_xpath
                ), f"Expected formatted xpath '{expected_xpath}', but got '{dom_data['xpath']}'"

                # Verify SelectorFactory was called with formatted XPath
                mock_factory.generate_relative_xpaths_from_full_xpath.assert_called_once_with(
                    full_xpath=expected_xpath
                )

    def test_bugninja_controller_initialization(
        self, bugninja_controller: BugninjaController
    ) -> None:
        """Test BugninjaController initialization with default parameters.

        This test validates that the BugninjaController is properly initialized
        with the expected default configuration. This ensures that the controller
        is ready for action processing and has the correct initial state.
        """
        assert isinstance(
            bugninja_controller, BugninjaController
        ), f"Expected BugninjaController instance, but got {type(bugninja_controller)}"
        assert bugninja_controller.verbose is True, "Expected verbose mode to be enabled by default"

    def test_bugninja_controller_with_exclude_actions(self) -> None:
        """Test BugninjaController initialization with exclude_actions parameter.

        This test validates that the controller can be initialized with
        excluded actions for customizing available functionality. This
        parameter is important for controlling which actions are available
        in specific automation scenarios.
        """
        exclude_actions = ["scroll_up", "scroll_down"]
        controller = BugninjaController(exclude_actions=exclude_actions, verbose=False)

        assert controller.verbose is False, "Expected verbose mode to be disabled when specified"
        # Note: We can't easily test exclude_actions without accessing internal registry

    def test_bugninja_controller_with_output_model(self) -> None:
        """Test BugninjaController initialization with custom output model.

        This test validates that the controller can be initialized with
        a custom output model for specialized action processing. This
        feature allows for custom action result types and validation.
        """

        class TestModel(BaseModel):
            test_field: str

        controller = BugninjaController(output_model=TestModel, verbose=True)
        assert controller.verbose is True, "Expected verbose mode to be enabled when specified"

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_down_action(
        self, bugninja_controller: BugninjaController, mock_browser_session: BrowserSession
    ) -> None:
        """Test scroll_down action with specified amount.

        This test validates that the scroll_down action correctly executes
        with a specified pixel amount, evaluates page height, and performs
        the scroll operation. This functionality is critical for page
        navigation and content exploration in browser automation.
        """
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)  # type: ignore[method-assign]
        mock_page.evaluate = AsyncMock(return_value=800)  # type: ignore[method-assign] # page height
        mock_page.wait_for_load_state = AsyncMock()  # type: ignore[method-assign]
        mock_page.mouse.wheel = AsyncMock()  # type: ignore[method-assign]

        scroll_action = ScrollAction(amount=500)

        # Execute scroll_down action using registry's execute_action method
        result = await bugninja_controller.registry.execute_action(
            action_name="scroll_down",
            params=scroll_action.model_dump(),
            browser_session=mock_browser_session,
        )

        # Verify results
        assert isinstance(
            result, ActionResult
        ), f"Expected ActionResult instance, but got {type(result)}"
        assert (
            "Scrolled down the page by 500 pixels" in result.extracted_content
        ), f"Expected scroll message in result, but got: {result.extracted_content}"
        assert result.include_in_memory is True, "Expected scroll action to be included in memory"

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.wait_for_load_state.assert_called_once_with("load")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=500)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_up_action(
        self, bugninja_controller: BugninjaController, mock_browser_session: BrowserSession
    ) -> None:
        """Test scroll_up action with specified amount.

        This test validates that the scroll_up action correctly executes
        with a specified pixel amount in the negative direction. This
        functionality enables upward navigation and content review in
        browser automation scenarios.
        """
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)  # type: ignore[method-assign]
        mock_page.evaluate = AsyncMock(return_value=800)  # type: ignore[method-assign] # page height
        mock_page.wait_for_load_state = AsyncMock()  # type: ignore[method-assign]
        mock_page.mouse.wheel = AsyncMock()  # type: ignore[method-assign]

        scroll_action = ScrollAction(amount=300)

        # Execute scroll_up action using registry's execute_action method
        result = await bugninja_controller.registry.execute_action(
            action_name="scroll_up",
            params=scroll_action.model_dump(),
            browser_session=mock_browser_session,
        )

        # Verify results
        assert isinstance(
            result, ActionResult
        ), f"Expected ActionResult instance, but got {type(result)}"
        assert (
            "Scrolled down the page by -300 pixels" in result.extracted_content
        ), f"Expected scroll message in result, but got: {result.extracted_content}"
        assert result.include_in_memory is True, "Expected scroll action to be included in memory"

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.wait_for_load_state.assert_called_once_with("load")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=-300)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_without_amount(
        self, bugninja_controller: BugninjaController, mock_browser_session: BrowserSession
    ) -> None:
        """Test scroll actions without specifying amount (should use page height).

        This test validates that scroll actions use the full page height
        when no specific amount is provided. This default behavior ensures
        complete page navigation when scroll distance is not specified.
        """
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)  # type: ignore[method-assign]
        mock_page.evaluate = AsyncMock(return_value=1000)  # type: ignore[method-assign] # page height
        mock_page.wait_for_load_state = AsyncMock()  # type: ignore[method-assign]
        mock_page.mouse.wheel = AsyncMock()  # type: ignore[method-assign]

        scroll_action = ScrollAction(amount=None)  # No amount specified

        # Execute scroll_down action using registry's execute_action method
        result = await bugninja_controller.registry.execute_action(
            action_name="scroll_down",
            params=scroll_action.model_dump(),
            browser_session=mock_browser_session,
        )

        # Verify results
        assert isinstance(
            result, ActionResult
        ), f"Expected ActionResult instance, but got {type(result)}"
        assert (
            "Scrolled down the page by 1000 pixels" in result.extracted_content
        ), f"Expected scroll message with page height, but got: {result.extracted_content}"

        # Verify page interactions
        mock_page.evaluate.assert_called_once_with("() => window.innerHeight")
        mock_page.mouse.wheel.assert_called_once_with(delta_x=0, delta_y=1000)

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_error_handling(
        self, bugninja_controller: BugninjaController, mock_browser_session: BrowserSession
    ) -> None:
        """Test error handling in scroll actions when page evaluation fails.

        This test validates that scroll actions properly handle exceptions
        when page evaluation fails. This error handling is critical for
        maintaining system stability when browser interactions encounter
        unexpected issues.
        """
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)  # type: ignore[method-assign]
        mock_page.evaluate = AsyncMock(side_effect=Exception("Page evaluation failed"))  # type: ignore[method-assign]

        scroll_action = ScrollAction(amount=100)

        # Execute scroll action using registry's execute_action method (should raise exception)
        with pytest.raises(Exception, match="Page evaluation failed"):
            await bugninja_controller.registry.execute_action(
                action_name="scroll_down",
                params=scroll_action.model_dump(),
                browser_session=mock_browser_session,
            )

    @pytest.mark.asyncio
    async def test_bugninja_controller_scroll_mouse_wheel_error(
        self, bugninja_controller: BugninjaController, mock_browser_session: BrowserSession
    ) -> None:
        """Test error handling when mouse.wheel fails during scroll action.

        This test validates that scroll actions properly handle exceptions
        when the mouse wheel operation fails. This error handling ensures
        that scroll failures are properly reported rather than silently
        ignored.
        """
        # Setup
        mock_page = MagicMock()
        mock_browser_session.get_current_page = AsyncMock(return_value=mock_page)  # type: ignore[method-assign]
        mock_page.evaluate = AsyncMock(return_value=800)  # type: ignore[method-assign]
        mock_page.wait_for_load_state = AsyncMock()  # type: ignore[method-assign]
        mock_page.mouse.wheel = AsyncMock(side_effect=Exception("Mouse wheel failed"))  # type: ignore[method-assign]

        scroll_action = ScrollAction(amount=100)

        # Execute scroll action using registry's execute_action method (should raise exception)
        with pytest.raises(Exception, match="Mouse wheel failed"):
            await bugninja_controller.registry.execute_action(
                action_name="scroll_down",
                params=scroll_action.model_dump(),
                browser_session=mock_browser_session,
            )

    def test_bugninja_controller_registry_actions(
        self, bugninja_controller: BugninjaController
    ) -> None:
        """Test that scroll actions are properly registered in the controller.

        This test validates that the scroll actions are available in the
        controller's registry. This registration is critical for ensuring
        that the actions can be called through the controller's action registry.
        """
        # Verify that the actions are available in the registry
        assert (
            "scroll_down" in bugninja_controller.registry.registry.actions
        ), "Expected scroll_down action to be available in controller registry"
        assert (
            "scroll_up" in bugninja_controller.registry.registry.actions
        ), "Expected scroll_up action to be available in controller registry"

        # Verify that the actions are callable through the registry
        assert callable(
            bugninja_controller.registry.registry.actions["scroll_down"]
        ), "Expected scroll_down to be callable through registry"
        assert callable(
            bugninja_controller.registry.registry.actions["scroll_up"]
        ), "Expected scroll_up to be callable through registry"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_all_selector_actions(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test extending all selector-oriented actions with DOM element data.

        This test validates that all selector-oriented action types are
        properly enriched with DOM element data. This comprehensive testing
        ensures that the DOM enrichment functionality works correctly for
        all supported action types in browser automation scenarios.
        """
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
                    action.model_dump.return_value = {  # type: ignore[method-assign]
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
                    assert (
                        len(result) == 1
                    ), f"Expected 1 extended action for {action_type}, but got {len(result)}"
                    extended_action = result[0]

                    # Verify DOM element data was added for all selector-oriented actions
                    assert (
                        extended_action.dom_element_data is not None
                    ), f"Expected DOM element data for {action_type} action"
                    assert (
                        extended_action.brain_state_id == brain_state_id
                    ), f"Expected brain_state_id to match for {action_type} action"
                    assert (
                        extended_action.action == action.model_dump()
                    ), f"Expected action to match original for {action_type}"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_missing_selector_map_entry(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_action_model: ActionModel,
    ) -> None:
        """Test handling when selector_map doesn't contain the required index.

        This test validates that the function gracefully handles cases where
        the selector_map is empty or doesn't contain the expected index.
        This error handling ensures system stability when processing actions
        with missing or invalid selector references.
        """
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
        assert len(result) == 1, f"Expected 1 action to be returned, but got {len(result)}"
        assert (
            result[0].action == mock_action_model.model_dump()
        ), "Expected returned action to match original action model"
        # DOM element data should be None since index wasn't found
        assert (
            result[0].dom_element_data is None
        ), "Expected no DOM element data when index not found in selector map"

    @pytest.mark.asyncio
    async def test_extend_agent_action_with_info_complex_action_structure(
        self,
        mock_page: Page,
        mock_browser_state_summary: BrowserStateSummary,
        mock_agent_output: AgentOutput,
        mock_dom_element_node: DOMElementNode,
    ) -> None:
        """Test extending actions with complex nested structures.

        This test validates that the function correctly processes complex
        action structures with nested parameters and options. This testing
        ensures that sophisticated action configurations are properly
        handled and enriched with DOM element data.
        """
        # Setup
        brain_state_id = "test_brain_id"
        mock_browser_state_summary.selector_map = {0: mock_dom_element_node}

        # Create complex action
        action = MagicMock()
        action.model_dump.return_value = {  # type: ignore[method-assign]
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
                assert len(result) == 1, f"Expected 1 extended action, but got {len(result)}"
                extended_action = result[0]

                # Verify complex action structure was preserved
                assert (
                    extended_action.action == action.model_dump()
                ), "Expected complex action structure to be preserved"
                assert (
                    extended_action.action["drag_drop"]["index"] == 0
                ), "Expected drag_drop index to be preserved"
                assert (
                    extended_action.action["drag_drop"]["target_index"] == 1
                ), "Expected drag_drop target_index to be preserved"
                assert (
                    extended_action.action["drag_drop"]["options"]["timeout"] == 5000
                ), "Expected drag_drop timeout option to be preserved"

                # Verify DOM element data was added
                assert (
                    extended_action.dom_element_data is not None
                ), "Expected DOM element data to be added for complex action"
