import logging
from typing import Any, Dict, List, Optional

from browser_use.agent.views import AgentBrain  # type: ignore
from browser_use.browser import BrowserProfile  # type: ignore
from browser_use.browser.profile import (  # type: ignore
    ClientCertificate,
    ColorScheme,
    Geolocation,
    ProxySettings,
    ViewportSize,
)
from pydantic import BaseModel, Field, NonNegativeFloat
from rich import print as rich_print

from src.utils.logger_config import set_logger_config

# Configure logging with custom format
set_logger_config()
logger = logging.getLogger(__name__)

#! State comparisons


class ElementComparison(BaseModel):
    """Represents the comparison result of a single element against expected state.

    This model stores the comparison details for a single element, including
    its index position, the reason for the comparison result, and whether
    the element matches the expected state.
    """

    index: int
    reason: str
    is_match: bool


class StateComparison(BaseModel):
    """Represents a collection of element comparisons for analyzing overall state.

    This model contains a list of `ElementComparison` objects and provides
    methods to analyze the overall state comparison results.
    """

    evaluation: List[ElementComparison]

    def get_equal_state_idx(self) -> Optional[int]:
        """Find the index of the first matching element in the evaluation.

        Returns:
            The index of the first matching element, or None if no matches found.
        """
        for idx, element in enumerate(self.evaluation):
            if element.is_match:
                return idx

        return None


class BugninjaExtendedAction(BaseModel):
    """Represents extended action data with brain state associations and DOM information.

    This model stores action data along with associated brain state ID and
    optional DOM element information for comprehensive action tracking.
    """

    brain_state_id: str
    action: Dict[str, Any]
    dom_element_data: Optional[Dict[str, Any]]
    screenshot_filename: Optional[str] = None


#! Traversal


class BugninjaBrowserConfig(BaseModel):
    """Browser configuration settings for automation scenarios.

    This model provides comprehensive browser configuration options including
    user agent, viewport settings, security settings, and network configurations
    for browser automation tasks.
    """

    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for browser automation",
    )
    viewport: Dict[str, int] = Field(
        default={"width": 1280, "height": 960},
        description="Viewport dimensions for browser automation",
    )
    device_scale_factor: Optional[NonNegativeFloat] = Field(default=None)
    color_scheme: ColorScheme = Field(default=ColorScheme.LIGHT)
    accept_downloads: bool = Field(default=False)
    proxy: Optional[ProxySettings] = Field(default=None)
    client_certificates: List[ClientCertificate] = Field(default_factory=list)
    extra_http_headers: Dict[str, str] = Field(default_factory=dict)
    http_credentials: Optional[Dict[str, str]] = Field(default=None)
    java_script_enabled: bool = Field(default=True)
    geolocation: Optional[Geolocation] = Field(default=None)
    timeout: float = Field(default=30_000)
    headers: Optional[Dict[str, str]] = Field(default=None)
    allowed_domains: Optional[List[str]] = Field(default=None)

    @staticmethod
    def from_browser_profile(browser_profile: BrowserProfile) -> "BugninjaBrowserConfig":
        """Convert external BrowserProfile to BugninjaBrowserConfig.

        Args:
            browser_profile: External browser profile to convert.

        Returns:
            BugninjaBrowserConfig instance with converted settings.
        """

        viewport: Optional[ViewportSize] = browser_profile.viewport
        viewport_element: Optional[Dict[str, int]] = None

        if viewport is not None:
            viewport_element = {
                "width": viewport.width,
                "height": viewport.height,
            }

        return BugninjaBrowserConfig(
            user_agent=browser_profile.user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport=viewport_element or {"width": 1280, "height": 960},
            device_scale_factor=browser_profile.device_scale_factor,
            color_scheme=browser_profile.color_scheme,
            accept_downloads=browser_profile.accept_downloads,
            proxy=browser_profile.proxy,
            client_certificates=browser_profile.client_certificates,
            extra_http_headers=browser_profile.extra_http_headers,
            http_credentials=browser_profile.http_credentials,
            java_script_enabled=browser_profile.java_script_enabled,
            geolocation=browser_profile.geolocation,
            timeout=browser_profile.timeout,
            headers=browser_profile.headers,
            allowed_domains=browser_profile.allowed_domains,
        )


class Traversal(BaseModel):
    """Complete test case data including browser configuration, brain states, and actions.

    This model represents a complete test case with all necessary components
    for browser automation including configuration, credentials, brain states,
    and action sequences.
    """

    test_case: str
    browser_config: BugninjaBrowserConfig
    secrets: Dict[str, str]
    brain_states: Dict[str, AgentBrain]
    actions: Dict[str, BugninjaExtendedAction]

    class Config:
        arbitrary_types_allowed = True


#! Healing Functionality State Machine


class BugninjaBrainState(AgentBrain):
    """Brain state data with unique identifier for state machine operations.

    This model extends `AgentBrain` with an ID field for tracking brain states
    in state machine scenarios and provides conversion methods for compatibility.
    """

    id: str

    def to_agent_brain(self) -> "AgentBrain":
        """Convert to AgentBrain for external system compatibility.

        Returns:
            AgentBrain instance without the ID field for external compatibility.
        """
        return AgentBrain(
            evaluation_previous_goal=self.evaluation_previous_goal,
            memory=self.memory,
            next_goal=self.next_goal,
        )


class ReplayWithHealingStateMachine(BaseModel):
    """State machine for managing replay scenarios with healing capabilities.

    This model manages state transitions, action execution, and healing
    mechanisms for robust automation scenarios with error recovery.
    """

    current_action: BugninjaExtendedAction
    current_brain_state: BugninjaBrainState

    replay_states: List[BugninjaBrainState]
    replay_actions: List[BugninjaExtendedAction]

    passed_brain_states: List[BugninjaBrainState] = Field(default_factory=list)
    passed_actions: List[BugninjaExtendedAction] = Field(default_factory=list)

    def complete_current_brain_state(self) -> None:
        """Complete the current brain state and move to the next state.

        This method moves the current brain state to the passed states list
        and updates the current brain state to the next one in the replay sequence.
        """
        # Add the current brain state to the passed list
        self.passed_brain_states.append(self.current_brain_state)
        self.current_brain_state = self.replay_states.pop(0)

    def replay_action_done(self) -> None:
        """Complete the current action and move to the next action.

        This method moves the current action to the passed actions list,
        updates to the next action, and triggers brain state completion
        if the action belongs to a different brain state.
        """
        rich_print("Current action BEFORE update")
        rich_print(self.current_action)

        # Add the current action to the passed list
        self.passed_actions.append(self.current_action)

        # Update to the next action
        self.current_action = self.replay_actions.pop(0)

        rich_print("Current action AFTER update")
        rich_print(self.current_action)

        if self.current_action.brain_state_id != self.current_brain_state.id:
            self.complete_current_brain_state()

    def complete_step_by_healing(self, healing_agent_actions: List[BugninjaExtendedAction]) -> None:
        """Complete current step using healing actions and update state machine.

        This method integrates healing actions into the state machine by adding
        them to passed actions, completing the current brain state, and updating
        the replay actions to skip previously healed actions.

        Args:
            healing_agent_actions: List of healing actions to integrate.
        """
        # Add the actions to the passed actions
        self.passed_actions.extend(healing_agent_actions)
        self.complete_current_brain_state()

        # Find the index of the action where it fits the brain_state_id
        index = [action.brain_state_id for action in self.replay_actions].index(
            self.current_brain_state.id
        )
        self.current_action = self.replay_actions[index]
        # Skip the actions previously healed
        self.replay_actions = self.replay_actions[index + 1 :]

    def set_new_current_state(self, brain_state_id: str) -> None:
        """Set the current state to a target brain state and update replay sequences.

        This method updates the current brain state to a target state and
        adjusts the replay states and actions accordingly for jump-to-state
        functionality in complex automation scenarios.

        Args:
            brain_state_id: ID of the target brain state to jump to.
        """
        # Find the index of the brain state where it fits the brain_state_id
        index = [state.id for state in self.replay_states].index(brain_state_id)
        self.current_brain_state = self.replay_states[index]
        # Skip the states previously healed
        self.replay_states = self.replay_states[index:]

        # Find the index of the action where it fits the brain_state_id
        index = [action.brain_state_id for action in self.replay_actions].index(brain_state_id)
        self.current_action = self.replay_actions[index]
        # Skip the actions previously healed
        self.replay_actions = self.replay_actions[index:]

    def add_healing_agent_brain_state_and_actions(
        self,
        healing_agent_brain_state: BugninjaBrainState,
        healing_actions: List[BugninjaExtendedAction],
    ) -> None:
        """Add healing brain state and actions to the passed collections.

        This method adds healing brain states and actions to the passed
        collections to maintain a complete history of both original and
        healing actions in the state machine.

        Args:
            healing_agent_brain_state: Brain state from healing agent.
            healing_actions: Actions performed by healing agent.
        """
        self.passed_brain_states.append(healing_agent_brain_state)
        self.passed_actions.extend(healing_actions)

    def replay_should_stop(self, healing_agent_reached_goal: bool, verbose: bool = False) -> bool:
        """Determine if the replay process should stop.

        This method evaluates whether the replay should stop based on whether
        the healing agent has reached its goal or if there are no remaining
        states to process.

        Args:
            healing_agent_reached_goal: Whether the healing agent has reached its goal.
            verbose: Whether to enable verbose logging for debugging.

        Returns:
            True if replay should stop, False otherwise.
        """
        remaining_state_num: int = len(self.replay_states)

        if verbose:
            logger.info(f"Number of remaining states: {remaining_state_num}")
            logger.info(f"Did healing agent reach the goal? '{remaining_state_num}'")

        # Either the healing agent reached the full goal of the test or there are no remaining steps to be done!
        return healing_agent_reached_goal or not remaining_state_num
