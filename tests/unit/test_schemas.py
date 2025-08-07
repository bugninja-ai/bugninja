from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from browser_use.agent.views import AgentBrain  # type:ignore
from browser_use.browser.profile import (  # type:ignore
    ColorScheme,
    ViewportSize,
)

from bugninja.schemas.pipeline import (
    BugninjaBrainState,
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    ElementComparison,
    ReplayWithHealingStateMachine,
)

# Import Polyfactory factories for test data generation
from tests.fixtures.models.schema_factories import (
    AgentBrainFactory,
    BrowserProfileMockFactory,
    BugninjaBrainStateFactory,
    BugninjaBrowserConfigFactory,
    BugninjaExtendedActionFactory,
    ElementComparisonFactory,
    ReplayWithHealingStateMachineFactory,
    StateComparisonFactory,
    TraversalFactory,
)


class TestElementComparison:
    """Test suite for `ElementComparison` model.

    This test suite validates the `ElementComparison` schema which represents
    the comparison result of a single element against expected state. These
    tests ensure that element comparisons are properly created, validated,
    and handle both positive and negative match scenarios correctly.
    """

    # ? VALID CASE
    @pytest.mark.parametrize(
        "index,reason,is_match",
        [
            (0, "First element match", True),
            (1, "Second element mismatch", False),
            (999, "Large index element", True),
            (0, "", False),  # Empty reason
        ],
    )
    def test_element_comparison_with_various_parameters(
        self, index: int, reason: str, is_match: bool
    ) -> None:
        """Test `ElementComparison` with various parameter combinations.

        This parameterized test validates that `ElementComparison` handles
        different input combinations correctly. Testing edge cases like
        empty strings and large indices ensures robust behavior across
        various real-world scenarios.
        """
        element_comp = ElementComparisonFactory.custom_build(
            index=index, reason=reason, is_match=is_match
        )

        # Verify all parameters are correctly applied - essential for data integrity
        assert element_comp.index == index, f"Index should be {index}"
        assert element_comp.reason == reason, f"Reason should be '{reason}'"
        assert element_comp.is_match == is_match, f"is_match should be {is_match}"


class TestStateComparison:
    """Test suite for `StateComparison` model.

    This test suite validates the `StateComparison` schema which represents
    a collection of element comparisons and provides methods to analyze
    the overall state comparison results. These tests ensure that state
    comparisons work correctly for various scenarios including matches,
    mismatches, and edge cases.
    """

    @pytest.fixture
    def sample_element_comparisons_with_mixed_results(self) -> List[ElementComparison]:
        """Create sample element comparisons with mixed match results for testing.

        This fixture provides realistic test data with both positive and
        negative matches. Having mixed results is crucial for testing
        the `get_equal_state_idx` method which needs to find the first
        matching element in a collection of comparisons.
        """
        return [
            ElementComparisonFactory.custom_build(
                index=0, reason="First element matches", is_match=True
            ),
            ElementComparisonFactory.custom_build(
                index=1, reason="Second element does not match", is_match=False
            ),
            ElementComparisonFactory.custom_build(
                index=2, reason="Third element does not match", is_match=False
            ),
        ]

    @pytest.fixture
    def sample_element_comparisons_with_no_match_found(self) -> List[ElementComparison]:
        """Create sample element comparisons with no match results for testing."""
        return [
            ElementComparisonFactory.custom_build(
                index=0, reason="First element does not match", is_match=False
            ),
            ElementComparisonFactory.custom_build(
                index=1, reason="Second element does not match", is_match=False
            ),
        ]

    @pytest.fixture
    def sample_element_comparisons_with_multiple_results(self) -> List[ElementComparison]:
        """Create sample element comparisons with multiple match results for testing."""
        return [
            ElementComparisonFactory.custom_build(
                index=0, reason="First element does match", is_match=True
            ),
            ElementComparisonFactory.custom_build(
                index=1, reason="Second element does not match", is_match=False
            ),
            ElementComparisonFactory.custom_build(
                index=2, reason="Second element does match", is_match=True
            ),
        ]

    # ? VALID CASE
    def test_get_equal_state_idx_returns_first_match_index(
        self, sample_element_comparisons_with_mixed_results: List[ElementComparison]
    ) -> None:
        """Test `get_equal_state_idx` method returns the index of the first matching element.

        This test validates the core functionality of `get_equal_state_idx` which
        is used to find the first matching state in a collection. This method
        is critical for state machine logic where we need to identify which
        state matches the current conditions.
        """
        # Create StateComparison with mixed results using Polyfactory
        state_comp = StateComparisonFactory.custom_build(
            evaluation=sample_element_comparisons_with_mixed_results
        )

        # Should return index of first matching element (index 0) - critical for state selection
        result = state_comp.get_equal_state_idx()
        assert result == 0, "Should return index 0 for the first matching element"

    # ? VALID CASE
    def test_get_equal_state_idx_returns_none_when_no_matches_exist(
        self, sample_element_comparisons_with_no_match_found: List[ElementComparison]
    ) -> None:
        """Test `get_equal_state_idx` method returns None when no matches are found.

        This test validates the edge case where no elements match the expected
        state. This scenario is important for error handling and debugging
        when state comparisons fail completely.
        """

        state_comp = StateComparisonFactory.custom_build(
            evaluation=sample_element_comparisons_with_no_match_found
        )

        # Should return None when no matches are found - essential for error handling
        result = state_comp.get_equal_state_idx()
        assert result is None, "Should return 'None' when no elements match"

    # ? VALID CASE
    def test_get_equal_state_idx_handles_empty_evaluation_collection(self) -> None:
        """Test `get_equal_state_idx` method handles empty evaluation collections.

        This test validates the edge case where the evaluation collection
        is empty. This scenario can occur in real-world situations where
        no elements are available for comparison, and proper handling
        prevents runtime errors.
        """
        # Create StateComparison with empty evaluation using Polyfactory
        state_comp = StateComparisonFactory.custom_build(evaluation=[])

        # Should return None for empty evaluation - prevents runtime errors
        result = state_comp.get_equal_state_idx()
        assert result is None, "Should return None for empty evaluation collection"

    # ? VALID CASE
    def test_get_equal_state_idx_returns_first_match_with_multiple_matches(
        self, sample_element_comparisons_with_multiple_results: List[ElementComparison]
    ) -> None:
        """Test `get_equal_state_idx` method returns the first match when multiple matches exist.

        This test validates that when multiple elements match, the method
        returns the index of the first match. This behavior is important
        for deterministic state selection and prevents ambiguity in
        state machine transitions.
        """

        state_comp = StateComparisonFactory.custom_build(
            evaluation=sample_element_comparisons_with_multiple_results
        )

        # Should return index of first matching element (index 0) - ensures deterministic behavior
        result = state_comp.get_equal_state_idx()
        assert result == 0, "Should return index 0 for the first match when multiple matches exist"

    # ? VALID CASE
    @pytest.mark.parametrize(
        "evaluation_data,expected_result",
        [
            ([], None),  # Empty evaluation
            ([ElementComparisonFactory.custom_build(is_match=False)], None),  # Single non-match
            ([ElementComparisonFactory.custom_build(is_match=True)], 0),  # Single match
            (
                [
                    ElementComparisonFactory.custom_build(is_match=False),
                    ElementComparisonFactory.custom_build(is_match=True),
                ],
                1,
            ),  # Match at index 1
            (
                [
                    ElementComparisonFactory.custom_build(is_match=True),
                    ElementComparisonFactory.custom_build(is_match=True),
                ],
                0,
            ),  # Multiple matches, returns first
        ],
    )
    def test_get_equal_state_idx_with_various_evaluation_scenarios(
        self, evaluation_data: List[ElementComparison], expected_result: Optional[int]
    ) -> None:
        """Test `get_equal_state_idx` method with various evaluation scenarios.

        This parameterized test validates the `get_equal_state_idx` method
        across different evaluation scenarios. Testing these various cases
        ensures robust behavior in real-world applications where state
        comparisons can have different patterns and edge cases.
        """
        state_comp = StateComparisonFactory.custom_build(evaluation=evaluation_data)
        result = state_comp.get_equal_state_idx()
        assert (
            result == expected_result
        ), f"Expected {expected_result}, got {result} for evaluation scenario"


class TestBugninjaExtendedAction:
    """Test suite for `BugninjaExtendedAction` model.

    This test suite validates the `BugninjaExtendedAction` schema which represents
    extended action data including brain state associations and DOM element
    information. These tests ensure that action data is properly structured
    and can handle various action types and DOM element configurations.
    """

    # ? VALID CASE
    def test_bugninja_extended_action_creation_with_valid_data(self) -> None:
        """Test creating `BugninjaExtendedAction` with valid data using Polyfactory.

        This test validates that `BugninjaExtendedAction` objects can be created
        with valid action data and DOM element information. This is essential
        for maintaining the integrity of action sequences and ensuring proper
        association between actions and brain states.
        """
        # Use Polyfactory to generate test data for consistent and maintainable tests
        extended_action = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id",
            action={"click_element_by_index": {"index": 0, "text": "Click the button"}},
            dom_element_data={
                "tag_name": "button",
                "attributes": {"id": "test-button"},
                "xpath": "//button[@id='test-button']",
            },
        )

        # Verify all fields are properly set - critical for action execution and data integrity
        assert (
            extended_action.brain_state_id == "test_brain_id"
        ), "Brain state ID should be correctly set"
        assert extended_action.action == {
            "click_element_by_index": {"index": 0, "text": "Click the button"}
        }, "Action data should match provided data"
        assert extended_action.dom_element_data == {
            "tag_name": "button",
            "attributes": {"id": "test-button"},
            "xpath": "//button[@id='test-button']",
        }, "DOM element data should match provided data"

    # ? VALID CASE
    def test_bugninja_extended_action_creation_without_dom_element_data(self) -> None:
        """Test creating `BugninjaExtendedAction` without DOM element data.

        This test validates that `BugninjaExtendedAction` objects can handle
        scenarios where DOM element data is not available. This is important
        for actions that don't require DOM element information, such as
        navigation actions or system-level operations.
        """
        # Use Polyfactory with custom parameters to test scenario without DOM data
        extended_action = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id",
            action={"goto": {"url": "https://example.com"}},
            dom_element_data=None,
        )

        # Verify action works correctly without DOM element data - important for navigation actions
        assert (
            extended_action.brain_state_id == "test_brain_id"
        ), "Brain state ID should be set even without DOM data"
        assert extended_action.action == {
            "goto": {"url": "https://example.com"}
        }, "Action data should be preserved"
        assert (
            extended_action.dom_element_data is None
        ), "DOM element data should be None when not provided"

    # ? VALID CASE
    def test_bugninja_extended_action_field_validation_and_types(self) -> None:
        """Test `BugninjaExtendedAction` field validation and type checking.

        This test ensures that all fields have the correct types and validation
        works properly. Type safety is critical for data integrity and prevents
        runtime errors when processing action data.
        """
        # Use Polyfactory to generate a valid instance for type testing
        extended_action = BugninjaExtendedActionFactory.custom_build()

        # Verify field types are correct - essential for data integrity and type safety
        assert isinstance(
            extended_action.brain_state_id, str
        ), "Brain state ID must be a string for proper identification"
        assert isinstance(
            extended_action.action, dict
        ), "Action must be a dictionary for flexible action representation"
        assert isinstance(
            extended_action.dom_element_data, dict
        ), "DOM element data must be a dictionary for structured element information"

    # ? VALID CASE
    @pytest.mark.parametrize(
        "action_type,dom_data",
        [
            ({"click_element_by_index": {"index": 6, "xpath": None}}, {"tag_name": "button"}),
            (
                {
                    "input_text": {
                        "index": 1,
                        "text": "Some input",
                        "xpath": None,
                    }
                },
                {"tag_name": "input"},
            ),
            ({"go_to_url": {"url": "https://example.com"}}, None),
            ({"wait": {"time": 1000}}, None),
        ],
    )
    def test_bugninja_extended_action_with_various_action_types(
        self, action_type: Dict[str, Any], dom_data: Optional[Dict[str, str]]
    ) -> None:
        """Test `BugninjaExtendedAction` with various action types and configurations.

        This parameterized test validates that `BugninjaExtendedAction` handles
        different action types correctly. Testing various action configurations
        ensures robust behavior across different automation scenarios.
        """
        extended_action = BugninjaExtendedActionFactory.custom_build(
            brain_state_id="test_brain_id", action=action_type, dom_element_data=dom_data
        )

        # Verify action data is correctly stored - ensures robust behavior across scenarios
        assert extended_action.action == action_type, f"Action should match provided {action_type}"
        assert (
            extended_action.dom_element_data == dom_data
        ), f"DOM data should match provided {dom_data}"
        assert (
            extended_action.brain_state_id == "test_brain_id"
        ), "Brain state ID should remain consistent"


class TestBugninjaBrowserConfig:
    """Test suite for `BugninjaBrowserConfig` model.

    This test suite validates the `BugninjaBrowserConfig` schema which represents
    browser configuration settings for automation. These tests ensure that
    browser configurations are properly created, validated, and can handle
    various browser profile scenarios including conversion from external
    browser profile objects.
    """

    # ? VALID CASE
    def test_bugninja_browser_config_creation_with_default_values(self) -> None:
        """Test `BugninjaBrowserConfig` creation with default values using Polyfactory.

        This test validates that `BugninjaBrowserConfig` objects are created
        with proper default values when no custom configuration is provided.
        Default values are critical for ensuring consistent browser behavior
        across different automation scenarios.
        """
        # Use Polyfactory to create config with default values
        config = BugninjaBrowserConfig.default_factory()

        # Verify all default values are correctly set - essential for consistent behavior across automation scenarios
        assert (
            config.user_agent
            == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ), "User agent should have default Chrome user agent"
        assert config.viewport == {
            "width": 1280,
            "height": 960,
        }, "Viewport should default to 1280x960"
        assert config.device_scale_factor is None, "Device scale factor should be None by default"
        assert config.color_scheme == ColorScheme.LIGHT, "Color scheme should default to LIGHT"
        assert config.accept_downloads is False, "Accept downloads should default to False"
        assert config.proxy is None, "Proxy should be None by default"
        assert (
            config.client_certificates == []
        ), "Client certificates should be empty list by default"
        assert config.extra_http_headers == {}, "Extra HTTP headers should be empty dict by default"
        assert config.http_credentials is None, "HTTP credentials should be None by default"
        assert config.java_script_enabled is True, "JavaScript should be enabled by default"
        assert config.geolocation is None, "Geolocation should be None by default"
        assert config.timeout == 30_000, "Timeout should default to 30 seconds"
        assert config.headers is None, "Headers should be None by default"
        assert config.allowed_domains is None, "Allowed domains should be None by default"

    # ? VALID CASE
    def test_bugninja_browser_config_creation_with_custom_values(self) -> None:
        """Test `BugninjaBrowserConfig` creation with custom values using Polyfactory.

        This test validates that `BugninjaBrowserConfig` objects can be created
        with custom configuration values. Custom configurations are essential
        for testing specific browser scenarios and ensuring that all
        configuration options work correctly.
        """
        # Use Polyfactory with custom parameters to test various configuration options
        config = BugninjaBrowserConfigFactory.build(
            user_agent="Test User Agent",
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2.0,
            color_scheme=ColorScheme.DARK,
            accept_downloads=True,
            timeout=60000.0,
            java_script_enabled=False,
            allowed_domains=["example.com", "test.com"],
        )

        # Verify all custom values are correctly applied - critical for configuration flexibility and testing specific scenarios
        assert config.user_agent == "Test User Agent", "User agent should match provided value"
        assert config.viewport == {
            "width": 1920,
            "height": 1080,
        }, "Viewport should match provided dimensions"
        assert config.device_scale_factor == 2.0, "Device scale factor should match provided value"
        assert config.color_scheme == ColorScheme.DARK, "Color scheme should match provided value"
        assert config.accept_downloads is True, "Accept downloads should match provided value"
        assert config.timeout == 60000.0, "Timeout should match provided value"
        assert config.java_script_enabled is False, "JavaScript enabled should match provided value"
        assert config.allowed_domains == [
            "example.com",
            "test.com",
        ], "Allowed domains should match provided list"

    # ? VALID CASE
    def test_from_browser_profile_conversion_with_viewport(self) -> None:
        """Test `from_browser_profile` method conversion with viewport using mock factory.

        This test validates the conversion from external BrowserProfile objects
        to `BugninjaBrowserConfig`. This conversion is critical for integrating
        with external browser automation libraries and ensuring compatibility
        with different browser profile formats.
        """
        # Use mock factory to create realistic browser profile with viewport
        mock_profile = BrowserProfileMockFactory.custom_build(
            user_agent="Test User Agent",
            device_scale_factor=1.5,
            color_scheme=ColorScheme.DARK,
            accept_downloads=True,
            proxy=None,
            client_certificates=[],
            extra_http_headers={"X-Test": "value"},
            http_credentials=None,
            java_script_enabled=False,
            geolocation=None,
            timeout=45000.0,
            headers={"User-Agent": "Custom Agent"},
            allowed_domains=["example.com"],
        )

        # Mock viewport with proper structure
        mock_viewport = MagicMock(spec=ViewportSize)
        mock_viewport.width = 1920
        mock_viewport.height = 1080
        mock_profile.viewport = mock_viewport

        # Convert to `BugninjaBrowserConfig` using the conversion method
        config = BugninjaBrowserConfig.from_browser_profile(mock_profile)

        # Verify all properties are correctly converted - essential for integration with external browser automation libraries
        assert config.user_agent == "Test User Agent", "User agent should be converted correctly"
        assert config.viewport == {
            "width": 1920,
            "height": 1080,
        }, "Viewport should be converted to dict format"
        assert (
            config.device_scale_factor == 1.5
        ), "Device scale factor should be converted correctly"
        assert config.color_scheme == ColorScheme.DARK, "Color scheme should be converted correctly"
        assert config.accept_downloads is True, "Accept downloads should be converted correctly"
        assert config.proxy is None, "Proxy should be converted correctly"
        assert config.client_certificates == [], "Client certificates should be converted correctly"
        assert config.extra_http_headers == {
            "X-Test": "value"
        }, "Extra HTTP headers should be converted correctly"
        assert config.http_credentials is None, "HTTP credentials should be converted correctly"
        assert (
            config.java_script_enabled is False
        ), "JavaScript enabled should be converted correctly"
        assert config.geolocation is None, "Geolocation should be converted correctly"
        assert config.timeout == 45000.0, "Timeout should be converted correctly"
        assert config.headers == {
            "User-Agent": "Custom Agent"
        }, "Headers should be converted correctly"
        assert config.allowed_domains == [
            "example.com"
        ], "Allowed domains should be converted correctly"

    # ? VALID CASE
    def test_from_browser_profile_conversion_without_viewport(self) -> None:
        """Test `from_browser_profile` method conversion without viewport using mock factory.

        This test validates the conversion from external BrowserProfile objects
        when viewport is not available. This scenario is important for
        compatibility with browser profiles that don't specify viewport
        dimensions.
        """
        # Use mock factory to create browser profile without viewport
        mock_profile = BrowserProfileMockFactory.custom_build(
            user_agent=None,  # Test with None user agent to ensure default is applied
            viewport=None,
            device_scale_factor=1.0,
            color_scheme=ColorScheme.LIGHT,
            accept_downloads=False,
            proxy=None,
            client_certificates=[],
            extra_http_headers={},
            http_credentials=None,
            java_script_enabled=True,
            geolocation=None,
            timeout=30_000,
            headers=None,
            allowed_domains=None,
        )

        # Convert to `BugninjaBrowserConfig` using the conversion method
        config = BugninjaBrowserConfig.from_browser_profile(mock_profile)

        # Verify conversion handles missing viewport and user agent correctly - important for compatibility with browser profiles that don't specify viewport dimensions
        assert (
            config.user_agent
            == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ), "User agent should default to Chrome user agent when not provided"
        assert config.viewport == {
            "width": 1280,
            "height": 960,
        }, "Viewport should default to 1280x960 when not provided"
        assert (
            config.device_scale_factor == 1.0
        ), "Device scale factor should be converted correctly"
        assert (
            config.color_scheme == ColorScheme.LIGHT
        ), "Color scheme should be converted correctly"
        assert config.accept_downloads is False, "Accept downloads should be converted correctly"


class TestTraversal:
    """Test suite for `Traversal` model.

    This test suite validates the `Traversal` schema which represents
    complete test case data including browser configuration, brain states,
    actions, and secrets. These tests ensure that traversal data is
    properly structured and can handle various test scenarios.
    """

    @pytest.fixture
    def sample_browser_config(self) -> BugninjaBrowserConfig:
        """Create sample browser config for testing using Polyfactory.

        This fixture provides a realistic browser configuration for testing
        traversal scenarios. Using Polyfactory ensures consistent and
        maintainable test data generation.
        """
        return BugninjaBrowserConfigFactory.build(
            user_agent="Test User Agent", viewport={"width": 1920, "height": 1080}
        )

    @pytest.fixture
    def sample_brain_states_dict(self) -> Dict[str, AgentBrain]:
        """Create sample brain states for testing using Polyfactory.

        This fixture provides realistic brain state data for testing
        traversal scenarios. Multiple brain states are essential for
        testing complex navigation sequences.
        """
        return {
            "brain_1": AgentBrainFactory.custom_build(
                evaluation_previous_goal="Goal evaluation 1",
                memory="Test memory 1",
                next_goal="Next goal 1",
            ),
            "brain_2": AgentBrainFactory.custom_build(
                evaluation_previous_goal="Goal evaluation 2",
                memory="Test memory 2",
                next_goal="Next goal 2",
            ),
        }

    @pytest.fixture
    def sample_actions_dict(self) -> Dict[str, BugninjaExtendedAction]:
        """Create sample actions for testing using Polyfactory.

        This fixture provides realistic action data for testing
        traversal scenarios. Multiple actions are essential for
        testing complex automation sequences.
        """
        return {
            "action_0": BugninjaExtendedActionFactory.custom_build(
                brain_state_id="brain_1",
                action={"click": {"selector": "button"}},
                dom_element_data={"tag_name": "button"},
            ),
            "action_1": BugninjaExtendedActionFactory.custom_build(
                brain_state_id="brain_2",
                action={"fill": {"selector": "input"}},
                dom_element_data={"tag_name": "input"},
            ),
        }

    # ? VALID CASE
    def test_traversal_creation_with_valid_data(
        self,
        sample_browser_config: BugninjaBrowserConfig,
        sample_brain_states_dict: Dict[str, AgentBrain],
        sample_actions_dict: Dict[str, BugninjaExtendedAction],
    ) -> None:
        """Test creating `Traversal` with valid data using Polyfactory.

        This test validates that `Traversal` objects can be created
        with valid test case data. This is essential for maintaining
        the integrity of test case data throughout the application.
        """
        # Use Polyfactory to create `Traversal` with realistic test data
        traversal = TraversalFactory.custom_build(
            test_case="Test navigation task",
            browser_config=sample_browser_config,
            secrets={"username": "test_user", "password": "test_pass"},
            brain_states=sample_brain_states_dict,
            actions=sample_actions_dict,
        )

        # Verify all fields are properly set - critical for test case execution and data integrity throughout the application
        assert (
            traversal.test_case == "Test navigation task"
        ), "Test case should match provided value"
        assert (
            traversal.browser_config == sample_browser_config
        ), "Browser config should match provided config"
        assert traversal.secrets == {
            "username": "test_user",
            "password": "test_pass",
        }, "Secrets should match provided data"
        assert (
            traversal.brain_states == sample_brain_states_dict
        ), "Brain states should match provided data"
        assert traversal.actions == sample_actions_dict, "Actions should match provided data"

    # ? VALID CASE

    def test_traversal_creation_with_empty_data(
        self, sample_browser_config: BugninjaBrowserConfig
    ) -> None:
        """Test `Traversal` creation with empty brain states and actions.

        This test validates that `Traversal` objects can handle scenarios
        where brain states and actions are empty. This is important for
        testing edge cases and initialization scenarios.
        """
        # Use Polyfactory to create `Traversal` with empty collections
        traversal = TraversalFactory.custom_build(
            test_case="Empty test case",
            browser_config=sample_browser_config,
            secrets={},
            brain_states={},
            actions={},
        )

        # Verify empty collections are handled correctly - important for testing edge cases and initialization scenarios
        assert traversal.test_case == "Empty test case", "Test case should match provided value"
        assert len(traversal.brain_states) == 0, "Brain states should be empty when not provided"
        assert len(traversal.actions) == 0, "Actions should be empty when not provided"


class TestBugninjaBrainState:
    """Test suite for `BugninjaBrainState` model.

    This test suite validates the `BugninjaBrainState` schema which represents
    brain state data with unique identifiers. These tests ensure that brain
    states are properly created, validated, and can be converted to
    AgentBrain objects for compatibility with external systems.
    """

    # ? VALID CASE
    def test_bugninja_brain_state_conversion_to_agent_brain(self) -> None:
        """Test converting `BugninjaBrainState` to AgentBrain using Polyfactory.

        This test validates the conversion from `BugninjaBrainState` to AgentBrain.
        This conversion is critical for integrating with external brain systems
        and ensuring compatibility with different brain state formats.
        """
        # Use Polyfactory to create a `BugninjaBrainState` for conversion testing
        bugninja_brain = BugninjaBrainStateFactory.custom_build(
            id="test_brain_id",
            evaluation_previous_goal="Goal evaluation",
            memory="Test memory",
            next_goal="Next goal",
        )

        # Convert to AgentBrain using the conversion method
        agent_brain = bugninja_brain.to_agent_brain()

        # Verify conversion preserves all brain state data - critical for integrating with external brain systems
        assert isinstance(agent_brain, AgentBrain), "Conversion should produce AgentBrain instance"
        assert (
            agent_brain.evaluation_previous_goal == "Goal evaluation"
        ), "Evaluation should be preserved"
        assert agent_brain.memory == "Test memory", "Memory should be preserved"
        assert agent_brain.next_goal == "Next goal", "Next goal should be preserved"

        # Verify id is not included in AgentBrain - important for compatibility with different brain state formats
        assert not hasattr(
            agent_brain, "id"
        ), "AgentBrain should not have id attribute for compatibility"

    # ? VALID CASE
    @pytest.mark.parametrize(
        "brain_id,evaluation,memory,next_goal",
        [
            ("brain_1", "Evaluation 1", "Memory 1", "Goal 1"),
            ("brain_2", "Evaluation 2", "Memory 2", "Goal 2"),
            ("complex_brain", "Complex evaluation", "Complex memory", "Complex goal"),
        ],
    )
    def test_bugninja_brain_state_with_various_data(
        self, brain_id: str, evaluation: str, memory: str, next_goal: str
    ) -> None:
        """Test `BugninjaBrainState` with various data combinations.

        This parameterized test validates that `BugninjaBrainState` handles
        different data combinations correctly. Testing various brain state
        configurations ensures robust behavior across different scenarios.
        """
        brain_state = BugninjaBrainStateFactory.custom_build(
            id=brain_id,
            evaluation_previous_goal=evaluation,
            memory=memory,
            next_goal=next_goal,
        )

        # Verify all parameters are correctly applied - ensures robust behavior across different scenarios
        assert brain_state.id == brain_id, f"Brain state ID should be {brain_id}"
        assert (
            brain_state.evaluation_previous_goal == evaluation
        ), f"Evaluation should be '{evaluation}'"
        assert brain_state.memory == memory, f"Memory should be '{memory}'"
        assert brain_state.next_goal == next_goal, f"Next goal should be '{next_goal}'"


class TestReplayWithHealingStateMachine:
    """Test suite for `ReplayWithHealingStateMachine` model.

    This test suite validates the `ReplayWithHealingStateMachine` schema which represents
    a state machine for managing replay scenarios with healing capabilities. These tests
    ensure that the state machine properly manages state transitions, action execution,
    and healing mechanisms for robust automation scenarios.
    """

    @pytest.fixture
    def sample_brain_states_list(self) -> List[BugninjaBrainState]:
        """Create sample brain states for testing using Polyfactory.

        This fixture provides realistic brain state data for testing
        state machine scenarios. Multiple brain states are essential for
        testing complex state transitions and healing mechanisms.
        """
        return [
            BugninjaBrainStateFactory.custom_build(
                id="brain_1",
                evaluation_previous_goal="Goal evaluation 1",
                memory="Test memory 1",
                next_goal="Next goal 1",
            ),
            BugninjaBrainStateFactory.custom_build(
                id="brain_2",
                evaluation_previous_goal="Goal evaluation 2",
                memory="Test memory 2",
                next_goal="Next goal 2",
            ),
            BugninjaBrainStateFactory.custom_build(
                id="brain_3",
                evaluation_previous_goal="Goal evaluation 3",
                memory="Test memory 3",
                next_goal="Next goal 3",
            ),
        ]

    @pytest.fixture
    def sample_actions_list(self) -> List[BugninjaExtendedAction]:
        """Create sample actions for testing using Polyfactory.

        This fixture provides realistic action data for testing
        state machine scenarios. Multiple actions are essential for
        testing complex action sequences and healing mechanisms.
        """
        return [
            BugninjaExtendedActionFactory.custom_build(
                brain_state_id="brain_1",
                action={
                    "click_element_by_index": {"index": 6, "xpath": None},
                },
                dom_element_data={"tag_name": "button"},
            ),
            BugninjaExtendedActionFactory.custom_build(
                brain_state_id="brain_2",
                action={
                    "input_text": {
                        "index": 1,
                        "text": "credential_1",
                        "xpath": None,
                    },
                },
                dom_element_data={"tag_name": "input"},
            ),
            BugninjaExtendedActionFactory.custom_build(
                brain_state_id="brain_3",
                action={
                    "input_text": {
                        "index": 2,
                        "text": "credential_2",
                        "xpath": None,
                    },
                },
                dom_element_data={"tag_name": "input"},
            ),
        ]

    @pytest.fixture
    def state_machine(
        self,
        sample_brain_states_list: List[BugninjaBrainState],
        sample_actions_list: List[BugninjaExtendedAction],
    ) -> ReplayWithHealingStateMachine:
        """Create `ReplayWithHealingStateMachine` instance for testing using Polyfactory.

        This fixture provides a properly initialized state machine for testing
        various state machine operations. The state machine is essential for
        testing replay scenarios and healing mechanisms.
        """
        return ReplayWithHealingStateMachine(
            current_action=sample_actions_list[0],
            current_brain_state=sample_brain_states_list[0],
            replay_states=sample_brain_states_list[1:].copy(),
            replay_actions=sample_actions_list[1:].copy(),
        )

    # ? VALID CASE
    def test_state_machine_creation_with_valid_data(
        self,
        sample_brain_states_list: List[BugninjaBrainState],
        sample_actions_list: List[BugninjaExtendedAction],
    ) -> None:
        """Test creating `ReplayWithHealingStateMachine` with valid data using Polyfactory.

        This test validates that `ReplayWithHealingStateMachine` objects can be created
        with valid state machine data. This is essential for maintaining
        the integrity of state machine data throughout the application.
        """
        # Use Polyfactory to create state machine with realistic data
        state_machine = ReplayWithHealingStateMachine(
            current_action=sample_actions_list[0],
            current_brain_state=sample_brain_states_list[0],
            replay_states=sample_brain_states_list.copy(),
            replay_actions=sample_actions_list.copy(),
        )

        # Verify all fields are properly initialized - critical for state machine operation and maintaining the integrity of state machine data
        assert (
            state_machine.current_action == sample_actions_list[0]
        ), "Current action should be set correctly"
        assert (
            state_machine.current_brain_state == sample_brain_states_list[0]
        ), "Current brain state should be set correctly"
        assert len(state_machine.replay_states) == 3, "Should have 3 replay states"
        assert len(state_machine.replay_actions) == 3, "Should have 3 replay actions"
        assert (
            len(state_machine.passed_brain_states) == 0
        ), "Passed brain states should be empty initially"
        assert len(state_machine.passed_actions) == 0, "Passed actions should be empty initially"

    # ? VALID CASE
    def test_complete_current_brain_state_transition(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test `complete_current_brain_state` method for proper state transitions.

        This test validates that the `complete_current_brain_state` method
        correctly moves the current brain state to the passed states list
        and updates the current brain state to the next one. This is
        critical for proper state machine progression and maintaining
        the integrity of state transitions.
        """
        initial_current_state = state_machine.current_brain_state
        initial_replay_states_count = len(state_machine.replay_states)
        initial_passed_states_count = len(state_machine.passed_brain_states)

        # Complete the current brain state
        state_machine.complete_current_brain_state()

        # Verify current brain state was moved to passed states - critical for proper state machine progression
        assert (
            len(state_machine.passed_brain_states) == initial_passed_states_count + 1
        ), "Should add one brain state to passed states"
        assert (
            state_machine.passed_brain_states[-1] == initial_current_state
        ), "Should add the current brain state to passed states"

        # Verify current brain state was updated to next state - essential for maintaining the integrity of state transitions
        assert (
            state_machine.current_brain_state != initial_current_state
        ), "Current brain state should be updated to next state"
        assert (
            len(state_machine.replay_states) == initial_replay_states_count - 1
        ), "Should remove one state from replay states"

    # ? VALID CASE
    def test_replay_action_done_transition(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test `replay_action_done` method for proper action transitions.

        This test validates that the `replay_action_done` method correctly
        moves the current action to the passed actions list and updates
        the current action to the next one. This is essential for
        proper action sequence progression and maintaining action history.
        """
        initial_current_action = state_machine.current_action
        initial_replay_actions_count = len(state_machine.replay_actions)
        initial_passed_actions_count = len(state_machine.passed_actions)

        # Complete the current action
        state_machine.replay_action_done()

        # Verify current action was moved to passed actions - essential for proper action sequence progression
        assert (
            len(state_machine.passed_actions) == initial_passed_actions_count + 1
        ), "Should add one action to passed actions"
        assert (
            state_machine.passed_actions[-1] == initial_current_action
        ), "Should add the current action to passed actions"

        # Verify current action was updated to next action - critical for maintaining action history
        assert (
            state_machine.current_action != initial_current_action
        ), "Current action should be updated to next action"
        assert (
            len(state_machine.replay_actions) == initial_replay_actions_count - 1
        ), "Should remove one action from replay actions"

    # ? VALID CASE
    def test_replay_action_done_with_brain_state_change(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test replay_action_done when brain state should change.

        This test validates that replay_action_done correctly handles
        scenarios where completing an action should also trigger a
        brain state change. This is important for maintaining
        synchronization between actions and brain states.
        """
        # Set up state machine so that next action has different brain state
        state_machine.current_action = state_machine.replay_actions[0]  # brain_1
        state_machine.current_brain_state = state_machine.replay_states[0]  # brain_1
        state_machine.replay_actions = state_machine.replay_actions[1:]  # Remove first action
        state_machine.replay_states = state_machine.replay_states[1:]  # Remove first state

        initial_current_brain_state = state_machine.current_brain_state
        initial_replay_states_count = len(state_machine.replay_states)

        # Complete the action which should trigger brain state change
        state_machine.replay_action_done()

        # Verify brain state was completed and moved to next - important for maintaining synchronization between actions and brain states
        assert len(state_machine.passed_brain_states) == 1, "Should complete one brain state"
        assert (
            state_machine.passed_brain_states[0] == initial_current_brain_state
        ), "Should add the current brain state to passed states"
        assert (
            state_machine.current_brain_state != initial_current_brain_state
        ), "Current brain state should be updated"
        assert (
            len(state_machine.replay_states) == initial_replay_states_count - 1
        ), "Should remove one state from replay states"

    # ? VALID CASE
    def test_complete_step_by_healing_with_healing_actions(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test 'complete_step_by_healing' method with healing actions.

        This test validates that the 'complete_step_by_healing' method
        correctly integrates healing actions into the state machine.
        Healing actions are crucial for handling scenarios where
        the original replay sequence fails and alternative actions
        are needed to recover.
        """
        # Create healing actions using Polyfactory
        healing_actions = [
            BugninjaExtendedActionFactory.custom_build(
                brain_state_id="healing_brain",
                action={
                    "click_element_by_index": {"index": 6, "xpath": None},
                },
                dom_element_data={"tag_name": "button"},
            )
        ]

        initial_passed_actions_count = len(state_machine.passed_actions)
        initial_replay_actions_count = len(state_machine.replay_actions)

        # Complete step using healing actions
        state_machine.complete_step_by_healing(healing_actions)

        # Verify healing actions were added to passed actions - crucial for handling scenarios where the original replay sequence fails
        assert (
            len(state_machine.passed_actions) == initial_passed_actions_count + 1
        ), "Should add healing action to passed actions"
        assert (
            state_machine.passed_actions[-1] == healing_actions[0]
        ), "Should add the healing action to passed actions"

        # Verify brain state was completed
        assert len(state_machine.passed_brain_states) == 1, "Should complete one brain state"

        # Verify replay actions were updated (skipped to next brain state) - essential for implementing alternative actions to recover
        assert (
            len(state_machine.replay_actions) < initial_replay_actions_count
        ), "Should update replay actions after healing"

    # ? VALID CASE
    def test_set_new_current_state_with_target_brain_state(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test `set_new_current_state` method with target brain state.

        This test validates that the `set_new_current_state` method
        correctly updates the current brain state to a target state
        and adjusts the replay states and actions accordingly.
        This is essential for implementing jump-to-state functionality
        in complex automation scenarios.
        """
        target_brain_state_id = "brain_3"

        initial_replay_states_count = len(state_machine.replay_states)
        initial_replay_actions_count = len(state_machine.replay_actions)

        # Set new current state to target brain state
        state_machine.set_new_current_state(target_brain_state_id)

        # Verify current brain state was updated to target - essential for implementing jump-to-state functionality in complex automation scenarios
        assert (
            state_machine.current_brain_state.id == target_brain_state_id
        ), "Current brain state should be updated to target"

        # Verify replay states and actions were updated
        assert (
            len(state_machine.replay_states) < initial_replay_states_count
        ), "Should update replay states"
        assert (
            len(state_machine.replay_actions) < initial_replay_actions_count
        ), "Should update replay actions"

    # ? VALID CASE
    def test_add_healing_agent_brain_state_and_actions(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test `add_healing_agent_brain_state_and_actions` method.

        This test validates that the `add_healing_agent_brain_state_and_actions`
        method correctly adds healing brain states and actions to the
        passed collections. This is important for maintaining a complete
        history of both original and healing actions in the state machine.
        """
        # Create healing brain state and actions using Polyfactory
        healing_brain_state = BugninjaBrainStateFactory.custom_build(
            id="healing_brain",
            evaluation_previous_goal="Healing evaluation",
            memory="Healing memory",
            next_goal="Healing goal",
        )

        healing_actions = [
            BugninjaExtendedActionFactory.custom_build(
                brain_state_id="healing_brain",
                action={"click_element_by_index": {"index": 6, "xpath": None}},
                dom_element_data={"tag_name": "button"},
            )
        ]

        initial_passed_states_count = len(state_machine.passed_brain_states)
        initial_passed_actions_count = len(state_machine.passed_actions)

        # Add healing brain state and actions
        state_machine.add_healing_agent_brain_state_and_actions(
            healing_brain_state, healing_actions
        )

        # Verify healing brain state was added to passed states - important for maintaining a complete history of both original and healing actions
        assert (
            len(state_machine.passed_brain_states) == initial_passed_states_count + 1
        ), "Should add healing brain state to passed states"
        assert (
            state_machine.passed_brain_states[-1] == healing_brain_state
        ), "Should add the healing brain state to passed states"

        # Verify healing actions were added to passed actions - essential for maintaining complete action history in the state machine
        assert (
            len(state_machine.passed_actions) == initial_passed_actions_count + 1
        ), "Should add healing action to passed actions"
        assert (
            state_machine.passed_actions[-1] == healing_actions[0]
        ), "Should add the healing action to passed actions"

    # ? VALID CASE
    def test_replay_should_stop_when_healing_agent_reached_goal(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test replay_should_stop when healing agent reached goal.

        This test validates that replay_should_stop returns True when
        the healing agent has reached its goal. This is important for
        determining when to stop the replay process after successful
        healing interventions.
        """
        result = state_machine.replay_should_stop(healing_agent_reached_goal=True)
        assert (
            result is True
        ), "Should stop replay when healing agent reached goal - important for determining when to stop the replay process after successful healing interventions"

    # ? VALID CASE
    def test_replay_should_stop_with_remaining_states(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test replay_should_stop when there are remaining states.

        This test validates that replay_should_stop returns False when
        there are remaining states to process and the healing agent
        has not reached its goal. This ensures the replay process
        continues until completion.
        """
        result = state_machine.replay_should_stop(healing_agent_reached_goal=False)
        assert (
            result is False
        ), "Should continue replay when there are remaining states - ensures the replay process continues until completion"

    # ? VALID CASE
    def test_replay_should_stop_with_no_remaining_states(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test replay_should_stop when there are no remaining states.

        This test validates that replay_should_stop returns True when
        there are no remaining states to process, regardless of the
        healing agent status. This ensures the replay process stops
        when all states have been processed.
        """
        # Clear replay states to simulate no remaining states
        state_machine.replay_states = []

        result = state_machine.replay_should_stop(healing_agent_reached_goal=False)
        assert (
            result is True
        ), "Should stop replay when no remaining states - ensures the replay process stops when all states have been processed"

    # ? VALID CASE
    def test_replay_should_stop_with_verbose_logging(
        self, state_machine: ReplayWithHealingStateMachine
    ) -> None:
        """Test replay_should_stop with verbose logging enabled.

        This test validates that replay_should_stop correctly handles
        verbose logging when enabled. Verbose logging is important for
        debugging complex state machine scenarios and understanding
        the decision-making process.
        """
        with patch("bugninja.schemas.logger") as mock_logger:
            state_machine.replay_should_stop(healing_agent_reached_goal=False, verbose=True)

            # Verify logging was called for debugging purposes - important for debugging complex state machine scenarios
            mock_logger.info.assert_called(), "Should log information when verbose mode is enabled"

    # ? VALID CASE
    def test_state_machine_with_empty_replay_data(self) -> None:
        """Test state machine with empty replay states and actions.

        This test validates that the state machine correctly handles
        edge cases where replay states and actions are empty. This
        scenario can occur during initialization or when all states
        have been processed, and proper handling prevents runtime errors.
        """
        # Create state machine with empty replay data using Polyfactory
        empty_state_machine = ReplayWithHealingStateMachineFactory.build(
            current_action=BugninjaExtendedActionFactory.custom_build(
                brain_state_id="test", action={}, dom_element_data=None
            ),
            current_brain_state=BugninjaBrainStateFactory.custom_build(
                id="test", evaluation_previous_goal="test", memory="test", next_goal="test"
            ),
            replay_states=[],
            replay_actions=[],
        )

        # Test replay_should_stop with empty states
        result = empty_state_machine.replay_should_stop(healing_agent_reached_goal=False)
        assert (
            result is True
        ), "Should stop replay when replay states are empty - prevents runtime errors when all states have been processed"
