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
    index: int
    reason: str
    is_match: bool


class StateComparison(BaseModel):
    evaluation: List[ElementComparison]

    def get_equal_state_idx(self) -> Optional[int]:
        for idx, element in enumerate(self.evaluation):
            if element.is_match:
                return idx

        return None


class BugninjaExtendedAction(BaseModel):
    brain_state_id: str
    action: Dict[str, Any]
    dom_element_data: Optional[Dict[str, Any]]


#! Traversal


class BugninjaBrowserConfig(BaseModel):
    user_agent: Optional[str] = Field(default=None)
    viewport: Optional[Dict[str, int]] = Field(default=None)
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

        viewport: Optional[ViewportSize] = browser_profile.viewport
        viewport_element: Optional[Dict[str, int]] = None

        if viewport is not None:
            viewport_element = {
                "width": viewport.width,
                "height": viewport.height,
            }

        return BugninjaBrowserConfig(
            user_agent=browser_profile.user_agent,
            viewport=viewport_element,
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
    test_case: str
    browser_config: BugninjaBrowserConfig
    secrets: Dict[str, str]
    brain_states: Dict[str, AgentBrain]
    actions: Dict[str, BugninjaExtendedAction]

    class Config:
        arbitrary_types_allowed = True


#! Healing Functionality State Machine


class BugninjaBrainState(AgentBrain):
    id: str

    def to_agent_brain(self) -> "AgentBrain":
        return AgentBrain(
            evaluation_previous_goal=self.evaluation_previous_goal,
            memory=self.memory,
            next_goal=self.next_goal,
        )


class ReplayWithHealingStateMachine(BaseModel):
    current_action: BugninjaExtendedAction
    current_brain_state: BugninjaBrainState

    replay_states: List[BugninjaBrainState]
    replay_actions: List[BugninjaExtendedAction]

    passed_brain_states: List[BugninjaBrainState] = Field(default_factory=list)
    passed_actions: List[BugninjaExtendedAction] = Field(default_factory=list)

    def complete_current_brain_state(self) -> None:
        # ? add the current brain state to the passed list
        self.passed_brain_states.append(self.current_brain_state)
        self.current_brain_state = self.replay_states.pop(0)

    def replay_action_done(self) -> None:

        rich_print("Current action BEFORE update")
        rich_print(self.current_action)

        # ? add the current action to the passed list
        self.passed_actions.append(self.current_action)

        # ? update to the next action
        self.current_action = self.replay_actions.pop(0)

        rich_print("Current action AFTER update")
        rich_print(self.current_action)

        if self.current_action.brain_state_id != self.current_brain_state.id:
            self.complete_current_brain_state()

    def complete_step_by_healing(self, healing_agent_actions: List[BugninjaExtendedAction]) -> None:
        # ? add the actions to the passed actions
        self.passed_actions.extend(healing_agent_actions)
        self.complete_current_brain_state()

        #! what will be the next action?
        # ? probably the first action of the next state
        #! we have to skip to the next action
        # ? find the index of the action where it fits the brain_state_id
        index = [action.brain_state_id for action in self.replay_actions].index(
            self.current_brain_state.id
        )
        self.current_action = self.replay_actions[index]
        # ? we skip the actions previously healed
        self.replay_actions = self.replay_actions[index + 1 :]

    def set_new_current_state(self, brain_state_id: str) -> None:

        #! we have to skip to the next brain state
        # ? find the index of the brain state where it fits the brain_state_id
        index = [state.id for state in self.replay_states].index(brain_state_id)
        self.current_brain_state = self.replay_states[index]
        # ? we skip the states previously healed
        self.replay_states = self.replay_states[index:]

        #! we have to skip to the next action
        # ? find the index of the action where it fits the brain_state_id
        index = [action.brain_state_id for action in self.replay_actions].index(brain_state_id)
        self.current_action = self.replay_actions[index]
        # ? we skip the actions previously healed
        self.replay_actions = self.replay_actions[index:]

    def add_healing_agent_brain_state_and_actions(
        self,
        healing_agent_brain_state: BugninjaBrainState,
        healing_actions: List[BugninjaExtendedAction],
    ) -> None:
        self.passed_brain_states.append(healing_agent_brain_state)
        self.passed_actions.extend(healing_actions)

    def replay_should_stop(self, healing_agent_reached_goal: bool, verbose: bool = False) -> bool:

        remaining_state_num: int = len(self.replay_states)

        if verbose:
            logger.info(f"Number of remaining states: {remaining_state_num}")
            logger.info(f"Did healing agent reach the goal? '{remaining_state_num}'")

        # ? either the healing agent reached the full goal of the test or there are no remaining steps to be done!
        return healing_agent_reached_goal or not remaining_state_num
