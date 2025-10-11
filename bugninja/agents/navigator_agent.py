import asyncio
import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID
from playwright._impl._api_structures import ViewportSize
from playwright.async_api import CDPSession
from rich import print as rich_print

from bugninja.agents.bugninja_agent_base import (
    NAVIGATION_IDENTIFIERS,
    BugninjaAgentBase,
)
from bugninja.agents.data_extraction_agent import DataExtractionAgent
from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.prompts.prompt_factory import (
    BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
    get_input_schema_prompt,
    get_io_extraction_prompt,
)
from bugninja.schemas.models import BugninjaConfig
from bugninja.schemas.pipeline import (
    ActionTimestamps,
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    Traversal,
)
from bugninja.schemas.test_case_io import TestCaseSchema
from bugninja.utils.logging_config import logger
from bugninja.utils.screenshot_manager import ScreenshotManager


class NavigatorAgent(BugninjaAgentBase):
    """Primary browser automation agent for task execution and traversal recording.

    This agent is the **main entry point** for browser automation tasks. It extends
    the base agent functionality with specialized capabilities for:
    - natural language task interpretation and execution
    - comprehensive action tracking and recording
    - screenshot capture for debugging and analysis
    - video recording of browser sessions for replay analysis
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

    def __init__(  # type:ignore
        self,
        *args,
        task: str,
        start_url: Optional[str],
        bugninja_config: BugninjaConfig,
        run_id: str | None = None,
        override_system_message: str = BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
        extra_instructions: List[str] = [],
        video_recording_config: VideoRecordingConfig | None = None,
        output_base_dir: Optional[Path] = None,
        screenshot_manager: Optional[ScreenshotManager] = None,
        io_schema: Optional[TestCaseSchema] = None,
        dependencies: Optional[List[str]] = None,
        original_task_secrets: Optional[Dict[str, Any]] = None,
        runtime_inputs: Optional[Dict[str, Any]] = None,
        **kwargs,  # type:ignore
    ) -> None:
        """Initialize NavigatorAgent with navigation-specific functionality.

        Args:
            *args: Arguments passed to the parent BugninjaAgentBase class
            task (str): The navigation task description for the agent to execute
            start_url (Optional[str]): URL where the browser session should start before executing the task
            run_id (str | None): Unique identifier for the current run. If None, generates a new CUID
            override_system_message (str): System message to override the default (defaults to navigator prompt)
            extra_instructions (List[str]): Additional instructions to append to the task
            video_recording_config (VideoRecordingConfig | None): Video recording configuration for session recording
            output_base_dir (Optional[Path]): Base directory for all output files (traversals, screenshots, videos)
            io_schema (Optional[TestCaseSchema]): Input/output schema for data extraction and input handling
            dependencies (Optional[List[str]]): List of task dependencies
            original_task_secrets (Optional[Dict[str, Any]]): Original task secrets (kept separate from runtime inputs)
            runtime_inputs (Optional[Dict[str, Any]]): Input data from dependent tasks to be included in system prompt
            **kwargs: Keyword arguments passed to the parent BugninjaAgentBase class
        """

        # Store unified schema and dependencies
        self.start_url = start_url
        self.io_schema = io_schema
        self.dependencies = dependencies or []
        self.original_task_secrets = original_task_secrets or {}

        # Initialize data extraction agent if output schema is defined
        self.data_extraction_agent: Optional[DataExtractionAgent] = None
        self.extracted_data: Dict[str, Any] = {}

        # Check if output schema exists and initialize extraction agent
        if self.io_schema and self.io_schema.output_schema:
            self.data_extraction_agent = DataExtractionAgent(
                cli_mode=getattr(self, "cli_mode", False)
            )

        # Add I/O extraction prompt to task description if output schema is defined
        if self.io_schema and self.io_schema.output_schema:
            io_prompt = get_io_extraction_prompt(self.io_schema.output_schema)
            if io_prompt:
                # Append to the task description
                task += f"\n\n{io_prompt}"

        # Prepare input schema system prompt extension if input data is provided
        input_schema_system_prompt: Optional[str] = None
        if self.io_schema and self.io_schema.input_schema and runtime_inputs:
            input_schema_system_prompt = get_input_schema_prompt(
                self.io_schema.input_schema, runtime_inputs
            )
            if input_schema_system_prompt:
                input_keys = list(self.io_schema.input_schema.keys())
                logger.bugninja_log(
                    f"📥 Agent: Task configured with {len(input_keys)} input data keys: {input_keys}"
                )

        super().__init__(
            *args,
            run_id=run_id,
            bugninja_config=bugninja_config,
            video_recording_config=video_recording_config,
            override_system_message=override_system_message,
            extend_system_message=input_schema_system_prompt,
            extra_instructions=extra_instructions,
            task=task,
            output_base_dir=output_base_dir,
            screenshot_manager=screenshot_manager,
            **kwargs,
        )

    async def _before_run_hook(self) -> None:
        """Initialize navigation session with event tracking and screenshot management.

        This hook sets up the navigation environment by:
        - initializing action and brain state tracking
        - setting up screenshot manager for navigation recording
        - initializing event tracking for navigation operations
        - logging the start of the navigation session
        - setting up browser isolation using run_id
        - setting up video recording if enabled
        - automatically navigating to the start_url programmatically
        """
        logger.bugninja_log("🏁 BEFORE-Run hook called")

        # Override user_data_dir with run_id for browser isolation
        if hasattr(self, "browser_session") and self.browser_session:
            base_dir = self.browser_session.browser_profile.user_data_dir or Path("./data_dir")
            if isinstance(base_dir, str):
                base_dir = Path(base_dir)
            isolated_dir = base_dir / f"run_{self.run_id}"
            self.browser_session.browser_profile.user_data_dir = isolated_dir

            logger.bugninja_log(f"🔒 Using isolated browser directory: {isolated_dir}")

        self._traversal: Optional[Traversal] = None  # Store traversal after successful run

        # Update video recording config with base directory if available
        if self.video_recording_config and self.output_base_dir:
            from bugninja.config.video_recording import VideoRecordingConfig

            self.video_recording_config = VideoRecordingConfig.with_base_dir(
                self.output_base_dir, **self.video_recording_config.model_dump()
            )

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
                logger.bugninja_log(f"🎯 Started navigation run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

        # Automatically navigate to start_url programmatically
        if self.start_url is None:
            raise ValueError(
                "start_url is required but not provided. Please set the start_url field in your BugninjaTask or task configuration file."
            )

        logger.bugninja_log(f"🌐 Automatically navigating to start URL: {self.start_url}")
        try:
            current_page = await self.browser_session.get_current_page()
            await current_page.goto(self.start_url)
            await self.wait_proper_load_state(current_page)
            logger.bugninja_log(f"✅ Successfully navigated to: {self.start_url}")
        except Exception as e:
            logger.error(f"❌ Failed to navigate to start URL {self.start_url}: {e}")
            raise

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
        logger.bugninja_log("✅ AFTER-Run hook called")

        # Stop video recording if enabled
        if self.video_recording_manager:
            stats = await self.video_recording_manager.stop_recording()
            logger.bugninja_log(
                f"🎥 Stopped video recording. Frames processed: {stats['frames_processed']}"
            )

        # Extract data if test case was successful AND extraction agent is available
        # Use same logic as client for consistency - success means no errors occurred
        if (
            self.state.last_result
            and not any(
                result.error
                for result in self.state.last_result
                if hasattr(result, "error") and result.error
            )
            and self.data_extraction_agent
            and self.io_schema
            and self.io_schema.output_schema
        ):

            try:
                self.extracted_data = (
                    await self.data_extraction_agent.extract_data_from_brain_states(
                        self.agent_brain_states, self.io_schema.output_schema
                    )
                )

                # Post-process extracted data to resolve secret references
                self.extracted_data = self._resolve_secret_references(self.extracted_data)

                logger.bugninja_log(f"📊 Extracted data: {self.extracted_data}")

                # Check if extraction was successful (at least one value is not None)
                if all(value is None for value in self.extracted_data.values()):
                    logger.warning("⚠️ Data extraction failed - no data extracted")
                    # Mark as failed test case
                    from browser_use.agent.views import ActionResult

                    self.state.last_result = [
                        ActionResult(
                            success=False,
                            error="Data extraction failed - necessary info extraction did not happen",
                        )
                    ]
                else:
                    # Log partial success
                    extracted_count = sum(
                        1 for value in self.extracted_data.values() if value is not None
                    )
                    total_count = len(self.extracted_data)
                    logger.bugninja_log(
                        f"📊 Data extraction successful: {extracted_count}/{total_count} values extracted"
                    )

            except Exception as e:
                logger.warning(f"Failed to extract data: {e}")
                self.extracted_data = {key: None for key in self.io_schema.output_schema.keys()}
                # Mark as failed test case
                from browser_use.agent.views import ActionResult

                self.state.last_result = [
                    ActionResult(
                        success=False,
                        error="Data extraction failed - necessary info extraction did not happen",
                    )
                ]

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
                logger.bugninja_log(f"✅ Completed navigation run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to complete event tracking: {e}")

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
        logger.bugninja_log("🪝 BEFORE-Step hook called")

        current_page: Page = await self.browser_session.get_current_page()

        await self.wait_proper_load_state(current_page)

        # Initialize video recording on the first step only
        if not hasattr(self, "_video_recording_initialized"):
            self._video_recording_initialized = False

        if not self._video_recording_initialized:
            if self.video_recording_manager and self.browser_session.browser_context:
                try:
                    cdp_session = await self.browser_session.browser_context.new_cdp_session(current_page)  # type: ignore

                    # Start video recording
                    output_file = f"run_{self.run_id}"
                    await self.video_recording_manager.start_recording(output_file, cdp_session)

                    # Setup CDP screencast
                    await cdp_session.send(
                        "Page.startScreencast",
                        {
                            "format": "jpeg",
                            "quality": self.video_recording_manager.config.quality,
                            "maxWidth": self.video_recording_manager.config.width,
                            "maxHeight": self.video_recording_manager.config.height,
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
                    logger.bugninja_log(f"🎥 Started video recording: {output_file}")
                except Exception as e:
                    logger.bugninja_log(
                        f"⚠️ Video recording failed: {e}. Task will continue without video recording."
                    )
                    # Disable video recording for this session
                    self.video_recording_manager = None
                    self._video_recording_initialized = True

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
        extended_taken_actions = await self.extend_model_output_with_info(
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

    async def _before_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Hook called before each action (no-op implementation).

        Args:
            action (ActionModel): The action about to be executed
        """
        logger.info(
            msg=f"🪝 BEFORE-Action hook called for action #{len(self.agent_taken_actions)+1} in traversal"
        )

        extended_action: BugninjaExtendedAction = self.current_step_extended_actions[
            action_idx_in_step
        ]

        # Capture start video offset if video recording is enabled
        if self.video_recording_manager and self.video_recording_manager.is_recording:
            start_timestamp = time.time() * 1000  # UTC timestamp in milliseconds

            # Calculate video offset
            video_start_offset = self.video_recording_manager.get_video_offset(start_timestamp)

            # Create timestamps object with only video offsets
            extended_action.timestamps = ActionTimestamps(video_start_offset=video_start_offset)

            logger.bugninja_log(f"🕐 Captured start video offset: {video_start_offset:.3f}s")
        else:
            logger.bugninja_log(
                f"⚠️ Video recording not enabled: manager={self.video_recording_manager is not None}, recording={self.video_recording_manager.is_recording if self.video_recording_manager else False}"
            )

        rich_print("Current brain state:")
        rich_print(self.agent_brain_states[extended_action.brain_state_id])

        # ? we take screenshot of every action BEFORE it happens except the "go_to_url" since it has to be taken after
        if extended_action.get_action_type() not in NAVIGATION_IDENTIFIERS:
            #! taking appropriate screenshot before each action
            await self.handle_taking_screenshot_for_action(extended_action=extended_action)

    async def _after_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Capture screenshot after action execution for debugging.

        This hook takes a screenshot after each action is completed,
        highlighting the element that was interacted with for debugging
        and analysis purposes.

        Args:
            action (ActionModel): The action that was just executed
        """

        logger.info(
            msg=f"🪝 AFTER-Action hook called for action #{len(self.agent_taken_actions)+1}"
        )

        extended_action: BugninjaExtendedAction = self.current_step_extended_actions[
            action_idx_in_step
        ]

        # Capture end video offset if video recording is enabled and timestamps exist
        if (
            self.video_recording_manager
            and self.video_recording_manager.is_recording
            and extended_action.timestamps is not None
        ):

            end_timestamp = time.time() * 1000  # UTC timestamp in milliseconds

            # Calculate video offset
            video_end_offset = self.video_recording_manager.get_video_offset(end_timestamp)

            # Update timestamps with end video offset
            extended_action.timestamps.video_end_offset = video_end_offset

            logger.bugninja_log(f"🕐 Captured end video offset: {video_end_offset:.3f}s")

        # ? we take screenshot of `go_to_url` action after it happens since before it the page is not loaded yet
        if extended_action.get_action_type() in NAVIGATION_IDENTIFIERS:
            #! taking appropriate screenshot before each action
            await self.handle_taking_screenshot_for_action(extended_action=extended_action)

        # ? adding the taken action to the list of agent actions
        self.agent_taken_actions.append(self.current_step_extended_actions[action_idx_in_step])

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
        # Use configured directory or fallback to default
        if hasattr(self, "output_base_dir") and self.output_base_dir:
            traversal_dir = self.output_base_dir / "traversals"
        else:
            traversal_dir = Path("./traversals")

        # Create traversals directory if it doesn't exist
        os.makedirs(traversal_dir, exist_ok=True)

        # Get current timestamp in a readable format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save the traversal data with timestamp and unique ID
        traversal_file = traversal_dir / f"traverse_{timestamp}_{self.run_id}.json"

        actions: Dict[str, Any] = {}

        logger.bugninja_log(f"👉 Number of actions: {len(self.agent_taken_actions)}")
        logger.bugninja_log(f"🗨️ Number of thoughts: {len(self.agent_brain_states)}")

        for idx, model_taken_action in enumerate(self.agent_taken_actions):

            if verbose:
                logger.bugninja_log(f"Step {idx + 1}:")
                logger.bugninja_log("Log:")
                logger.bugninja_log(str(model_taken_action))

            # Log screenshot filename if present
            if model_taken_action.screenshot_filename:
                logger.bugninja_log(
                    f"📸 Action {idx} has screenshot: {model_taken_action.screenshot_filename}"
                )

            actions[f"action_{idx}"] = model_taken_action.model_dump()

        # Use the unified schema object (already processed by client)
        schema_obj = self.io_schema

        traversal = Traversal(
            test_case=self.raw_task,
            start_url=self.start_url,
            extra_instructions=self.extra_instructions,
            # TODO! saving here does not seem proper
            browser_config=BugninjaBrowserConfig.from_browser_profile(
                self.browser_session.browser_profile,
                window_size=ViewportSize(
                    width=self.bugninja_config.viewport_width,
                    height=self.bugninja_config.viewport_height,
                ),
            ),
            secrets=self.original_task_secrets,
            brain_states=self.agent_brain_states,
            actions=actions,
            input_schema=schema_obj.input_schema if schema_obj else None,
            output_schema=schema_obj.output_schema if schema_obj else None,
            extracted_data=self.extracted_data,
            dependencies=getattr(self, "dependencies", []),
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
        logger.bugninja_log(f"Traversal saved with ID: {timestamp}_{self.run_id}")

        return traversal

    async def _handle_screencast_frame(
        self, frame: dict[str, Any], cdp_session: CDPSession
    ) -> None:
        """Handle incoming screencast frames for video recording.

        Args:
            frame: CDP screencast frame data
            cdp_session: CDP session for acknowledgment
        """
        if self.video_recording_manager:
            try:
                img_data: bytes = base64.b64decode(frame["data"])
                arr: np.ndarray = np.frombuffer(img_data, np.uint8)  # type: ignore
                img: Optional[np.ndarray] = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # type: ignore

                if img is not None:
                    img = cv2.resize(
                        img,
                        (
                            self.video_recording_manager.config.width,
                            self.video_recording_manager.config.height,
                        ),
                    )
                    frame_bytes: bytes = img.tobytes()
                    await self.video_recording_manager.add_frame(frame_bytes)
            except Exception:
                pass
            finally:
                try:
                    await cdp_session.send(
                        "Page.screencastFrameAck", {"sessionId": frame["sessionId"]}
                    )
                except Exception:
                    pass
