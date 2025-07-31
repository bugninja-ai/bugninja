"""
Polyfactory factories for generating test data for schema models.

This module provides factories for creating test instances of all schema models
used in the bugninja application. Using Polyfactory ensures consistent and
maintainable test data generation while reducing code duplication.
"""

from typing import Any, Dict, Tuple
from unittest.mock import MagicMock

from browser_use.agent.views import AgentBrain  # type:ignore
from browser_use.browser.profile import ColorScheme  # type:ignore
from polyfactory.factories.pydantic_factory import ModelFactory
from typing_extensions import Unpack

from bugninja.schemas.pipeline import (
    BugninjaBrainState,
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    ReplayWithHealingStateMachine,
    Traversal,
)


class BugninjaExtendedActionFactory(ModelFactory[BugninjaExtendedAction]):
    """ModelFactory for generating BugninjaExtendedAction test instances.

    This factory creates BugninjaExtendedAction objects with realistic
    action data and DOM element information. It supports various action
    types and DOM element configurations for comprehensive testing.
    """

    __model__ = BugninjaExtendedAction

    @classmethod
    def custom_build(
        cls, **kwargs: Unpack[Tuple[str, Dict[str, Any], Dict[str, Any]]]
    ) -> BugninjaExtendedAction:
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
        return super().build(factory_use_construct=False, **defaults)


class BugninjaBrowserConfigFactory(ModelFactory[BugninjaBrowserConfig]):
    """ModelFactory for generating BugninjaBrowserConfig test instances.

    This factory creates BugninjaBrowserConfig objects with realistic
    browser configuration settings. It provides various configurations
    for testing different browser profiles and settings.
    """

    __model__ = BugninjaBrowserConfig


class AgentBrainFactory(ModelFactory[AgentBrain]):
    """ModelFactory for generating AgentBrain test instances.

    This factory creates AgentBrain objects for testing brain state
    functionality. It provides realistic brain state data for various
    testing scenarios.
    """

    @classmethod
    def custom_build(cls, **kwargs: Unpack[Tuple[str, str, str]]) -> AgentBrain:
        """Build an AgentBrain instance with default values."""
        defaults = {
            "evaluation_previous_goal": "Goal evaluation completed successfully",
            "memory": "Test memory content",
            "next_goal": "Proceed to next step",
        }
        defaults.update(kwargs)
        return AgentBrain(factory_use_construct=False, **defaults)


class BugninjaBrainStateFactory(ModelFactory[BugninjaBrainState]):
    """ModelFactory for generating BugninjaBrainState test instances.

    This factory creates BugninjaBrainState objects with realistic
    brain state data. It ensures all required fields are properly set
    and provides various brain state configurations for testing.
    """

    __model__ = BugninjaBrainState

    @classmethod
    def custom_build(cls, **kwargs: Unpack[Tuple[str, str, str, str]]) -> BugninjaBrainState:
        """Build a BugninjaBrainState instance with default values."""
        defaults = {
            "id": "test_brain_id",
            "evaluation_previous_goal": "Goal evaluation completed",
            "memory": "Test memory content",
            "next_goal": "Proceed to next goal",
        }
        defaults.update(kwargs)
        return super().build(factory_use_construct=False, **defaults)


class TraversalFactory(ModelFactory[Traversal]):
    """ModelFactory for generating Traversal test instances.

    This factory creates Traversal objects with realistic test case data,
    browser configurations, and action sequences. It provides comprehensive
    test data for navigation and traversal testing scenarios.
    """

    __model__ = Traversal

    @classmethod
    def custom_build(
        cls,
        **kwargs: Unpack[
            Tuple[
                str,
                BugninjaBrowserConfig,
                Dict[str, Any],
                Dict[str, AgentBrain],
                Dict[str, BugninjaExtendedAction],
            ]
        ],
    ) -> Traversal:
        """Build a Traversal instance with default values."""
        defaults = {
            "test_case": "Test navigation task",
            "browser_config": BugninjaBrowserConfigFactory.build(),
            "secrets": {"username": "test_user", "password": "test_pass"},
            "brain_states": {
                "brain_1": AgentBrainFactory.custom_build(),
                "brain_2": AgentBrainFactory.custom_build(),
            },
            "actions": {
                "action_0": BugninjaExtendedActionFactory.custom_build(),
                "action_1": BugninjaExtendedActionFactory.custom_build(),
            },
        }
        defaults.update(kwargs)
        return super().build(factory_use_construct=False, **defaults)


class ReplayWithHealingStateMachineFactory(ModelFactory[ReplayWithHealingStateMachine]):
    """ModelFactory for generating ReplayWithHealingStateMachine test instances.

    This factory creates ReplayWithHealingStateMachine objects with realistic
    state machine data. It provides various configurations for testing
    replay scenarios and healing mechanisms.
    """

    __model__ = ReplayWithHealingStateMachine


# Mock factories for external dependencies
class BrowserProfileMockFactory:
    """ModelFactory for creating mock BrowserProfile instances.

    This factory creates realistic mock BrowserProfile objects for testing
    browser configuration conversion scenarios.
    """

    @classmethod
    def custom_build(cls, **kwargs: Unpack[Tuple[Dict[str, Any]]]) -> MagicMock:
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
