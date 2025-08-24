import asyncio
import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID
from playwright.async_api import CDPSession

from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
from bugninja.agents.extensions import BugninjaController, extend_agent_action_with_info
from bugninja.schemas.pipeline import (
    BugninjaBrowserConfig,
    Traversal,
)
from bugninja.utils.screenshot_manager import ScreenshotManager


class NavigatorAgent(BugninjaAgentBase):
    """Primary browser automation agent for task execution and traversal recording.

    This agent is the **main entry point** for browser automation tasks. It extends
    the base agent functionality with specialized capabilities for:
    - natural language task interpretation and execution
    - comprehensive action tracking and recording
    - screenshot capture for debugging and analysis
    - traversal data serialization for replay scenarios
    - event publishing for operation monitoring

    The NavigatorAgent creates complete traversal records that can be replayed
    later with self-healing capabilities.

    Attributes:
        agent_taken_actions (List[BugninjaExtendedAction]): All actions taken during navigation
        agent_brain_states (Dict[str, AgentBrain]): Brain states throughout the navigation session
        _traversal (Optional[Traversal]): The completed traversal object after successful run
        screenshot_manager (ScreenshotManager): Manager for capturing navigation screenshots

    ### Key Methods

    1. *async* **_before_run_hook()** -> `None`: - Initialize navigation session and event tracking
    2. *async* **_after_run_hook()** -> `None`: - Complete navigation and save traversal data
    3. *async* **_before_step_hook()** -> `None`: - Process actions and create extended actions
    4. *async* **_after_action_hook()** -> `None`: - Capture screenshots after each action
    5. **save_agent_actions()** -> `Traversal`: - Serialize complete session data to JSON
    6. *async* **run()** -> `Optional[AgentHistoryList]`: - Execute navigation task

    Example:
        ```python
        from bugninja.agents.navigator_agent import NavigatorAgent
        from bugninja.events import EventPublisherManager

        # Create navigator agent with event tracking
        navigator = NavigatorAgent(
            task="Navigate to example.com and click the login button",
            llm=create_llm_model_from_config(create_llm_config_from_settings()),  # Uses unified LLM configuration
            browser_session=browser_session,
            event_manager=event_manager
        )

        # Execute navigation task
        result = await navigator.run(max_steps=50)

        # Access the created traversal
        if navigator._traversal:
            print(f"Traversal saved with {len(navigator._traversal.actions)} actions")
        ```
    """

    async def _before_run_hook(self) -> None:
        """Initialize navigation session with event tracking and screenshot management.

        This hook sets up the navigation environment by:
        - initializing action and brain state tracking
        - overriding the default controller with BugninjaController
        - setting up screenshot manager for navigation recording
        - initializing event tracking for navigation operations
        - logging the start of the navigation session
        - setting up browser isolation using run_id
        - setting up video recording if enabled
        """
        self._log_if_not_background("info", "🏁 BEFORE-Run hook called")

        # Override user_data_dir with run_id for browser isolation
        if hasattr(self, "browser_session") and self.browser_session:
            base_dir = self.browser_session.browser_profile.user_data_dir or Path("./data_dir")
            if isinstance(base_dir, str):
                base_dir = Path(base_dir)
            isolated_dir = base_dir / f"run_{self.run_id}"
            self.browser_session.browser_profile.user_data_dir = isolated_dir

            self._log_if_not_background(
                "info", f"🔒 Using isolated browser directory: {isolated_dir}"
            )

        self._traversal: Optional[Traversal] = None  # Store traversal after successful run

        #! we override the default controller with our own
        self.controller = BugninjaController()

        # Initialize screenshot manager
        self.screenshot_manager = ScreenshotManager(run_id=self.run_id, folder_prefix="traversal")

        # Setup video recording if enabled

        # Initialize event tracking for navigation run (if event_manager is provided)
        if self.event_manager and self.event_manager.has_publishers():
            try:
                await self.event_manager.initialize_run(
                    run_type="navigation",
                    metadata={
                        "task_description": self.task,
                        "target_url": getattr(self, "target_url", None),
                    },
                    existing_run_id=self.run_id,  # Use existing run_id instead of generating new one
                )
                self._log_if_not_background("info", f"🎯 Started navigation run: {self.run_id}")
            except Exception as e:
                self._log_if_not_background("warning", f"Failed to initialize event tracking: {e}")

    async def _after_run_hook(self) -> None:
        """Complete navigation session and save traversal data.

        This hook finalizes the navigation session by:
        - saving all agent actions and brain states
        - creating a complete traversal object
        - completing event tracking for navigation operations
        - stopping video recording if enabled
        - logging completion status for monitoring

        The hook ensures that all navigation data is properly serialized
        for later replay and analysis.
        """
        self._log_if_not_background("info", "✅ AFTER-Run hook called")

        # Stop video recording if enabled
        if self.video_recording_manager:
            stats = await self.video_recording_manager.stop_recording()
            self._log_if_not_background(
                "info", f"🎥 Stopped video recording. Frames processed: {stats['frames_processed']}"
            )

        # Save agent actions and store traversal
        self._traversal = self.save_agent_actions()

        # Complete event tracking for navigation run
        if self.event_manager:
            if not self.state.last_result:
                raise Exception("No results found for navigation run")
            try:
                success = not any(
                    result.error for result in self.state.last_result if hasattr(result, "error")
                )
                await self.event_manager.complete_run(self.run_id, success)
                self._log_if_not_background("info", f"✅ Completed navigation run: {self.run_id}")
            except Exception as e:
                self._log_if_not_background("warning", f"Failed to complete event tracking: {e}")

    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """Process actions and create extended actions for navigation operations.

        This hook is called before each step in the navigation process and:
        - creates brain state tracking for the current step
        - generates extended actions with DOM element information
        - associates actions with their extended versions
        - stores actions for later serialization and analysis
        - initializes video recording on the first step

        Args:
            browser_state_summary (BrowserStateSummary): Current browser state information
            model_output (AgentOutput): Model output containing actions to be executed
        """
        self._log_if_not_background("info", "🪝 BEFORE-Step hook called")

        current_page: Page = await self.browser_session.get_current_page()

        # Initialize video recording on the first step only
        if not hasattr(self, "_video_recording_initialized"):
            self._video_recording_initialized = False

        if not self._video_recording_initialized:
            if (
                self.video_recording_manager
                and self.video_recording_config
                and self.browser_session.browser_context
            ):
                cdp_session = await self.browser_session.browser_context.new_cdp_session(current_page)  # type: ignore

                # Start video recording
                output_file = f"run_{self.run_id}"
                await self.video_recording_manager.start_recording(output_file, cdp_session)

                # Setup CDP screencast
                await cdp_session.send(
                    "Page.startScreencast",
                    {
                        "format": "jpeg",
                        "quality": self.video_recording_config.quality,
                        "maxWidth": self.video_recording_config.width,
                        "maxHeight": self.video_recording_config.height,
                        "everyNthFrame": 1,
                    },
                )

                # Setup frame handler
                cdp_session.on(
                    "Page.screencastFrame",
                    lambda frame: asyncio.create_task(
                        self._handle_screencast_frame(frame, cdp_session)
                    ),
                )

                self._video_recording_initialized = True
                self._log_if_not_background("info", f"🎥 Started video recording: {output_file}")

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        extended_taken_actions = await extend_agent_action_with_info(
            brain_state_id=brain_state_id,
            current_page=current_page,
            model_output=model_output,
            browser_state_summary=browser_state_summary,
        )

        # Store extended actions for hook access
        self.current_step_extended_actions = extended_taken_actions

        # Associate each action with its corresponding extended action index
        for i, action in enumerate(model_output.action):
            self._associate_action_with_extended_action(action, i)

        # ? adding the taken actions to the list of agent actions
        self.agent_taken_actions.extend(extended_taken_actions)

    async def _after_step_hook(
        self, browser_state_summary: BrowserStateSummary, model_output: AgentOutput
    ) -> None:
        """Clean up action mapping after step completion.

        This hook clears the action mapping to prevent memory accumulation
        and ensure clean state for the next step.

        Args:
            browser_state_summary (BrowserStateSummary): Browser state after step completion
            model_output (AgentOutput): Model output from the completed step
        """
        # Clear action mapping to prevent memory accumulation
        self._clear_action_mapping()

    async def _before_action_hook(self, action: ActionModel) -> None:
        """Hook called before each action (no-op implementation).

        Args:
            action (ActionModel): The action about to be executed
        """
        ...

    async def _after_action_hook(self, action: ActionModel) -> None:
        """Capture screenshot after action execution for navigation recording.

        This hook takes a screenshot after each action is completed,
        highlighting the element that was interacted with for navigation
        recording and analysis purposes.

        Args:
            action (ActionModel): The action that was just executed
        """
        await self.browser_session.remove_highlights()

        current_page = await self.browser_session.get_current_page()

        # Get the extended action for screenshot with highlighting
        extended_action = self._find_matching_extended_action(action)
        if extended_action:
            # Take screenshot and get filename
            screenshot_filename = await self.screenshot_manager.take_screenshot(
                current_page, extended_action, self.browser_session
            )

            # Store screenshot filename with extended action
            extended_action.screenshot_filename = screenshot_filename
            self._log_if_not_background(
                "info", f"📸 Stored screenshot filename: {screenshot_filename}"
            )

    def save_agent_actions(self, verbose: bool = False) -> Traversal:
        """Save the agent's traversal data to a JSON file for analysis and replay.

        This function serializes the complete agent session data including all taken actions,
        brain states, browser configuration, and test case information into a structured
        JSON file. The file is saved in a 'traversals' directory with a timestamped filename
        for easy identification and organization.

        Args:
            verbose (bool): If True, logs detailed information about each action during the saving process

        Returns:
            Traversal: The created traversal object containing all session data

        Notes:
            - Creates a 'traversals' directory if it doesn't exist
            - Generates a unique traversal ID using CUID for collision-free naming
            - Uses timestamp format: YYYYMMDD_HHMMSS for chronological sorting
            - File naming convention: traverse_{timestamp}_{traversal_id}.json
            - Saves the following data structure:
                - test_case: The original task/objective
                - browser_config: Browser profile configuration
                - secrets: Sensitive data used during the session
                - brain_states: Agent's cognitive states throughout the session
                - actions: All actions taken by the agent with DOM element data
            - Actions are indexed as "action_0", "action_1", etc.
            - Logs the number of actions and brain states for monitoring
            - Uses pretty-printed JSON with 4-space indentation for readability
            - Handles Unicode characters properly with ensure_ascii=False
        """
        traversal_dir = Path("./traversals")

        # Create traversals directory if it doesn't exist
        os.makedirs(traversal_dir, exist_ok=True)

        # Get current timestamp in a readable format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save the traversal data with timestamp and unique ID
        traversal_file = traversal_dir / f"traverse_{timestamp}_{self.run_id}.json"

        actions: Dict[str, Any] = {}

        self._log_if_not_background(
            "info", f"👉 Number of actions: {len(self.agent_taken_actions)}"
        )
        self._log_if_not_background("info", f"🗨️ Number of thoughts: {len(self.agent_brain_states)}")

        for idx, model_taken_action in enumerate(self.agent_taken_actions):

            if verbose:
                self._log_if_not_background("info", f"Step {idx + 1}:")
                self._log_if_not_background("info", "Log:")
                self._log_if_not_background("info", str(model_taken_action))

            # Log screenshot filename if present
            if model_taken_action.screenshot_filename:
                self._log_if_not_background(
                    "info",
                    f"📸 Action {idx} has screenshot: {model_taken_action.screenshot_filename}",
                )

            actions[f"action_{idx}"] = model_taken_action.model_dump()

        traversal = Traversal(
            test_case=self.task,
            browser_config=BugninjaBrowserConfig.from_browser_profile(self.browser_profile),
            secrets=self.sensitive_data,
            brain_states=self.agent_brain_states,
            actions=actions,
        )

        with open(traversal_file, "w") as f:
            json.dump(
                traversal.model_dump(),
                f,
                indent=4,
                ensure_ascii=False,
            )

        # Store the traversal object for later access
        self._traversal = traversal

        # Only save to file if not in background mode
        if not self.background:
            with open(traversal_file, "w") as f:
                json.dump(
                    traversal.model_dump(),
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
            self._log_if_not_background(
                "info", f"Traversal saved with ID: {timestamp}_{self.run_id}"
            )
        else:
            self._log_if_not_background(
                "info", f"Traversal created (not saved to file) with ID: {timestamp}_{self.run_id}"
            )

        return traversal

    async def _handle_screencast_frame(
        self, frame: dict[str, Any], cdp_session: CDPSession
    ) -> None:
        """Handle incoming screencast frames for video recording.

        Args:
            frame: CDP screencast frame data
            cdp_session: CDP session for acknowledgment
        """
        if self.video_recording_manager and self.video_recording_config:
            try:
                img_data: bytes = base64.b64decode(frame["data"])
                arr: np.ndarray = np.frombuffer(img_data, np.uint8)  # type: ignore
                img: Optional[np.ndarray] = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # type: ignore

                if img is not None:
                    img = cv2.resize(
                        img, (self.video_recording_config.width, self.video_recording_config.height)
                    )
                    frame_bytes: bytes = img.tobytes()
                    await self.video_recording_manager.add_frame(frame_bytes)
            except Exception:
                pass
            finally:
                await cdp_session.send("Page.screencastFrameAck", {"sessionId": frame["sessionId"]})
