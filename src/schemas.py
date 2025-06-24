from typing import Any, Dict, List, Optional, Tuple

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

#! State comparisons


class ElementComparison(BaseModel):
    index: int
    reason: str
    equals: bool


class StateComparison(BaseModel):
    evaluation: List[ElementComparison]


class BugninjaExtendedAction(BaseModel):
    brain_state_id: str
    action: Dict[str, Any]
    dom_element_data: Optional[Dict[str, Any]]


#! Brain State Progress Tracking


class BrainStateAction(BaseModel):
    """Represents an action within a brain state with proper typing."""

    action_key: str
    action: BugninjaExtendedAction
    completed: bool = False
    failed: bool = False
    healer_replacement: Optional[BugninjaExtendedAction] = None


class BrainStateProgress(BaseModel):
    """Tracks the progress of a single brain state."""

    brain_state_id: str
    original_actions: List[BrainStateAction]
    completed_actions: List[BrainStateAction] = Field(default_factory=list)
    failed_action_index: Optional[int] = None
    healer_actions: List[BugninjaExtendedAction] = Field(default_factory=list)
    status: str = Field(default="in_progress")  # "in_progress" | "completed" | "failed"

    def is_complete(self) -> bool:
        """Check if brain state is complete (all actions done including healer replacements)."""
        total_actions = len(self.original_actions)
        completed_count = len(self.completed_actions) + len(self.healer_actions)
        return completed_count >= total_actions

    def is_exactly_complete(self) -> bool:
        """Check if brain state is exactly complete (no extra actions)."""
        total_actions = len(self.original_actions)
        completed_count = len(self.completed_actions) + len(self.healer_actions)
        return completed_count == total_actions

    def get_remaining_actions(self) -> int:
        """Get the number of remaining actions to complete this brain state."""
        total_actions = len(self.original_actions)
        completed_count = len(self.completed_actions) + len(self.healer_actions)
        return max(0, total_actions - completed_count)

    def mark_action_completed(self, action_key: str) -> None:
        """Mark an action as completed."""
        for action in self.original_actions:
            if action.action_key == action_key and not action.completed:
                action.completed = True
                self.completed_actions.append(action)
                break

    def mark_action_failed(self, action_index: int) -> None:
        """Mark an action as failed."""
        self.failed_action_index = action_index
        if 0 <= action_index < len(self.original_actions):
            self.original_actions[action_index].failed = True

    def add_healer_action(self, healer_action: BugninjaExtendedAction) -> None:
        """Add a healer action as replacement."""
        self.healer_actions.append(healer_action)

    def get_current_action(self, action_index: int) -> Optional[BrainStateAction]:
        """Get the current action at the specified index."""
        if 0 <= action_index < len(self.original_actions):
            return self.original_actions[action_index]
        return None

    def get_actions_for_execution(self) -> List[BugninjaExtendedAction]:
        """Get the list of actions in execution order (original + healer replacements)."""
        execution_actions = []

        for i, action in enumerate(self.original_actions):
            if action.completed:
                execution_actions.append(action.action)
            elif action.failed:
                # Find healer replacement for this action
                healer_index = i - len([a for a in self.original_actions[:i] if a.completed])
                if healer_index < len(self.healer_actions):
                    execution_actions.append(self.healer_actions[healer_index])

        return execution_actions


class BrainStateProgressTracker(BaseModel):
    """Manages progress tracking for all brain states."""

    brain_states: Dict[str, BrainStateProgress] = Field(default_factory=dict)
    current_brain_state_id: Optional[str] = None
    current_action_within_state: int = 0

    def initialize_from_traversal(
        self, traversal_actions: Dict[str, BugninjaExtendedAction]
    ) -> None:
        """Initialize brain state progress from traversal actions."""
        # Group actions by brain state
        brain_state_actions: Dict[str, List[Tuple[str, BugninjaExtendedAction]]] = {}
        for action_key, action in traversal_actions.items():
            brain_state_id = action.brain_state_id
            if brain_state_id not in brain_state_actions:
                brain_state_actions[brain_state_id] = []
            brain_state_actions[brain_state_id].append((action_key, action))

        # Create BrainStateProgress for each brain state
        for brain_state_id, actions in brain_state_actions.items():
            brain_state_actions_list = [
                BrainStateAction(action_key=action_key, action=action)
                for action_key, action in actions
            ]

            self.brain_states[brain_state_id] = BrainStateProgress(
                brain_state_id=brain_state_id, original_actions=brain_state_actions_list
            )

    def get_next_brain_state(self) -> Optional[str]:
        """Get the next brain state that needs processing."""
        for brain_state_id, progress in self.brain_states.items():
            if not progress.is_complete():
                return brain_state_id
        return None

    def set_current_brain_state(self, brain_state_id: str) -> None:
        """Set the current brain state being processed."""
        self.current_brain_state_id = brain_state_id
        self.current_action_within_state = 0

    def get_current_brain_state(self) -> Optional[BrainStateProgress]:
        """Get the current brain state progress."""
        if self.current_brain_state_id:
            return self.brain_states.get(self.current_brain_state_id)
        return None

    def get_current_actions(self) -> List[BrainStateAction]:
        """Get the actions for the current brain state."""
        current_state = self.get_current_brain_state()
        if current_state:
            return current_state.original_actions
        return []

    def mark_action_completed(self, action_key: str) -> None:
        """Mark an action as completed in the current brain state."""
        current_state = self.get_current_brain_state()
        if current_state:
            current_state.mark_action_completed(action_key)
            self.current_action_within_state += 1

    def mark_action_failed(self, action_index: int) -> None:
        """Mark an action as failed in the current brain state."""
        current_state = self.get_current_brain_state()
        if current_state:
            current_state.mark_action_failed(action_index)

    def add_healer_action(self, healer_action: BugninjaExtendedAction) -> None:
        """Add a healer action to the current brain state."""
        current_state = self.get_current_brain_state()
        if current_state:
            current_state.add_healer_action(healer_action)

    def get_completion_stats(self) -> Dict[str, int]:
        """Get completion statistics."""
        total_states = len(self.brain_states)
        completed_states = sum(
            1 for progress in self.brain_states.values() if progress.is_complete()
        )

        total_original_actions = sum(
            len(progress.original_actions) for progress in self.brain_states.values()
        )
        total_completed_actions = sum(
            len(progress.completed_actions) for progress in self.brain_states.values()
        )
        total_healer_actions = sum(
            len(progress.healer_actions) for progress in self.brain_states.values()
        )

        return {
            "total_states": total_states,
            "completed_states": completed_states,
            "total_original_actions": total_original_actions,
            "total_completed_actions": total_completed_actions,
            "total_healer_actions": total_healer_actions,
        }

    def build_corrected_actions(self) -> Dict[str, BugninjaExtendedAction]:
        """Build corrected actions including healer replacements."""
        corrected_actions = {}
        action_counter = 0

        for brain_state_id, progress in self.brain_states.items():
            if progress.is_complete():
                # Add original completed actions
                for action in progress.completed_actions:
                    corrected_actions[f"action_{action_counter}"] = action.action
                    action_counter += 1

                # Add healer actions as replacements
                for healer_action in progress.healer_actions:
                    corrected_actions[f"action_{action_counter}"] = healer_action
                    action_counter += 1

        return corrected_actions


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
