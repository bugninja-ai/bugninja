"""
Polyfactory factories for generating test data for schema models.

This module provides factories for creating test instances of all schema models
used in the bugninja application. Using Polyfactory ensures consistent and
maintainable test data generation while reducing code duplication.
"""

from unittest.mock import MagicMock

from browser_use.agent.views import AgentBrain
from browser_use.browser.profile import ColorScheme
from polyfactory.factories.pydantic_factory import ModelFactory

from src.schemas.pipeline import (
    BugninjaBrainState,
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    ElementComparison,
    ReplayWithHealingStateMachine,
    StateComparison,
    Traversal,
)


class ElementComparisonFactory(ModelFactory[ElementComparison]):
    """ModelFactory for generating ElementComparison test instances.

    This factory creates valid ElementComparison objects for testing.
    The factory ensures all required fields are properly set and provides
    realistic test data that covers various scenarios including positive
    and negative matches.
    """

    __model__ = ElementComparison

    @classmethod
    def build(cls, **kwargs) -> ElementComparison:
        """Build an ElementComparison instance with default values."""
        defaults = {
            "index": 0,
            "reason": "Element matches expected state",
            "is_match": True,
        }
        defaults.update(kwargs)
        return super().build(**defaults)


class StateComparisonFactory(ModelFactory[StateComparison]):
    """ModelFactory for generating StateComparison test instances.

    This factory creates StateComparison objects with realistic evaluation
    data. It provides various scenarios including matches, non-matches,
    and empty evaluations to test different edge cases.
    """

    __model__ = StateComparison

    @classmethod
    def build(cls, **kwargs) -> StateComparison:
        """Build a StateComparison instance with default values."""
        defaults = {
            "evaluation": [
                ElementComparisonFactory.build(index=0, is_match=True),
                ElementComparisonFactory.build(index=1, is_match=False),
                ElementComparisonFactory.build(index=2, is_match=True),
            ]
        }
        defaults.update(kwargs)
        return super().build(**defaults)


class BugninjaExtendedActionFactory(ModelFactory[BugninjaExtendedAction]):
    """ModelFactory for generating BugninjaExtendedAction test instances.

    This factory creates BugninjaExtendedAction objects with realistic
    action data and DOM element information. It supports various action
    types and DOM element configurations for comprehensive testing.
    """

    __model__ = BugninjaExtendedAction

    @classmethod
    def build(cls, **kwargs) -> BugninjaExtendedAction:
        """Build a BugninjaExtendedAction instance with default values."""
        defaults = {
            "brain_state_id": "test_brain_id",
            "action": {"click_element_by_index": {"index": 0, "text": "Click the button"}},
            "dom_element_data": {
                "tag_name": "button",
                "attributes": {"id": "test-button"},
                "xpath": "//button[@id='test-button']",
            },
        }
        defaults.update(kwargs)
        return super().build(**defaults)


class BugninjaBrowserConfigFactory(ModelFactory[BugninjaBrowserConfig]):
    """ModelFactory for generating BugninjaBrowserConfig test instances.

    This factory creates BugninjaBrowserConfig objects with realistic
    browser configuration settings. It provides various configurations
    for testing different browser profiles and settings.
    """

    __model__ = BugninjaBrowserConfig

    # @classmethod
    # def build(cls, **kwargs) -> BugninjaBrowserConfig:
    #     """Build a BugninjaBrowserConfig instance with default values."""
    #     # defaults = {
    #     #     "user_agent": "Test User Agent",
    #     #     "viewport": {"width": 1920, "height": 1080},
    #     #     "device_scale_factor": 1.0,
    #     #     "color_scheme": ColorScheme.LIGHT,
    #     #     "accept_downloads": False,
    #     #     "timeout": 30_000,
    #     #     "java_script_enabled": True,
    #     # }
    #     # defaults.update(kwargs)
    #     return super().build()


class AgentBrainFactory(ModelFactory[AgentBrain]):
    """ModelFactory for generating AgentBrain test instances.

    This factory creates AgentBrain objects for testing brain state
    functionality. It provides realistic brain state data for various
    testing scenarios.
    """

    @classmethod
    def build(cls, **kwargs) -> AgentBrain:
        """Build an AgentBrain instance with default values."""
        defaults = {
            "evaluation_previous_goal": "Goal evaluation completed successfully",
            "memory": "Test memory content",
            "next_goal": "Proceed to next step",
        }
        defaults.update(kwargs)
        return AgentBrain(**defaults)


class BugninjaBrainStateFactory(ModelFactory[BugninjaBrainState]):
    """ModelFactory for generating BugninjaBrainState test instances.

    This factory creates BugninjaBrainState objects with realistic
    brain state data. It ensures all required fields are properly set
    and provides various brain state configurations for testing.
    """

    __model__ = BugninjaBrainState

    @classmethod
    def build(cls, **kwargs) -> BugninjaBrainState:
        """Build a BugninjaBrainState instance with default values."""
        defaults = {
            "id": "test_brain_id",
            "evaluation_previous_goal": "Goal evaluation completed",
            "memory": "Test memory content",
            "next_goal": "Proceed to next goal",
        }
        defaults.update(kwargs)
        return super().build(**defaults)


class TraversalFactory(ModelFactory[Traversal]):
    """ModelFactory for generating Traversal test instances.

    This factory creates Traversal objects with realistic test case data,
    browser configurations, and action sequences. It provides comprehensive
    test data for navigation and traversal testing scenarios.
    """

    __model__ = Traversal

    @classmethod
    def build(cls, **kwargs) -> Traversal:
        """Build a Traversal instance with default values."""
        defaults = {
            "test_case": "Test navigation task",
            "browser_config": BugninjaBrowserConfigFactory.build(),
            "secrets": {"username": "test_user", "password": "test_pass"},
            "brain_states": {
                "brain_1": AgentBrainFactory.build(),
                "brain_2": AgentBrainFactory.build(),
            },
            "actions": {
                "action_0": BugninjaExtendedActionFactory.build(),
                "action_1": BugninjaExtendedActionFactory.build(),
            },
        }
        defaults.update(kwargs)
        return super().build(**defaults)


class ReplayWithHealingStateMachineFactory(ModelFactory[ReplayWithHealingStateMachine]):
    """ModelFactory for generating ReplayWithHealingStateMachine test instances.

    This factory creates ReplayWithHealingStateMachine objects with realistic
    state machine data. It provides various configurations for testing
    replay scenarios and healing mechanisms.
    """

    __model__ = ReplayWithHealingStateMachine

    # @classmethod
    # def build(cls, **kwargs) -> ReplayWithHealingStateMachine:
    #     """Build a ReplayWithHealingStateMachine instance with default values."""
    #     brain_states = [
    #         BugninjaBrainStateFactory.build(id="brain_1"),
    #         BugninjaBrainStateFactory.build(id="brain_2"),
    #         BugninjaBrainStateFactory.build(id="brain_3"),
    #     ]

    #     actions = [
    #         BugninjaExtendedActionFactory.build(brain_state_id="brain_1"),
    #         BugninjaExtendedActionFactory.build(brain_state_id="brain_2"),
    #         BugninjaExtendedActionFactory.build(brain_state_id="brain_3"),
    #     ]

    #     defaults = {
    #         "current_action": actions[0],
    #         "current_brain_state": brain_states[0],
    #         "replay_states": brain_states.copy(),
    #         "replay_actions": actions.copy(),
    #     }
    #     defaults.update(kwargs)
    #     return super().build(**defaults)


# Mock factories for external dependencies
class BrowserProfileMockFactory:
    """ModelFactory for creating mock BrowserProfile instances.

    This factory creates realistic mock BrowserProfile objects for testing
    browser configuration conversion scenarios.
    """

    @classmethod
    def build(cls, **kwargs) -> MagicMock:
        """Build a mock BrowserProfile instance with default values."""
        mock_profile = MagicMock()
        defaults = {
            "user_agent": "Test User Agent",
            "device_scale_factor": 1.0,
            "color_scheme": ColorScheme.LIGHT,
            "accept_downloads": False,
            "proxy": None,
            "client_certificates": [],
            "extra_http_headers": {},
            "http_credentials": None,
            "java_script_enabled": True,
            "geolocation": None,
            "timeout": 30_000,
            "headers": None,
            "allowed_domains": None,
        }
        defaults.update(kwargs)

        for key, value in defaults.items():
            setattr(mock_profile, key, value)

        return mock_profile
