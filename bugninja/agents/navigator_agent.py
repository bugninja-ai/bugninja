import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from browser_use.agent.service import logger  # type: ignore
from browser_use.agent.views import (  # type: ignore
    AgentBrain,
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID

from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
from bugninja.agents.extensions import BugninjaController, extend_agent_action_with_info
from bugninja.schemas.pipeline import (
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    Traversal,
)
from bugninja.utils.screenshot_manager import ScreenshotManager


class NavigatorAgent(BugninjaAgentBase):

    async def _before_run_hook(self) -> None:
        logger.info(msg="🏁 BEFORE-Run hook called")

        self.agent_taken_actions: List[BugninjaExtendedAction] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

        #! we override the default controller with our own
        self.controller = BugninjaController()

        # Initialize screenshot manager
        self.screenshot_manager = ScreenshotManager(folder_prefix="traversal")

        # Initialize event tracking for navigation run (if event_manager is provided)
        if self.event_manager and self.event_manager.has_publishers():
            try:
                run_id = await self.event_manager.initialize_run(
                    run_type="navigation",
                    metadata={
                        "task_description": self.task,
                        "target_url": getattr(self, "target_url", None),
                    },
                )
                self.run_id = run_id
                logger.info(f"🎯 Started navigation run: {run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

    async def _after_run_hook(self) -> None:
        """Complete event tracking for navigation run.

        This hook finalizes the event tracking for navigation runs,
        marking the run as completed or failed based on the final result.
        """
        logger.info(msg="✅ AFTER-Run hook called")
        self.save_agent_actions()

        # Complete event tracking for navigation run
        if self.event_manager and self.run_id:
            try:
                success = not any(
                    result.error for result in self.state.last_result if hasattr(result, "error")
                )
                await self.event_manager.complete_run(self.run_id, success)
                logger.info(f"✅ Completed navigation run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to complete event tracking: {e}")

    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:

        logger.info(msg="🪝 BEFORE-Step hook called")

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        current_page: Page = await self.browser_session.get_current_page()

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
        # Clear action mapping to prevent memory accumulation
        self._clear_action_mapping()

    async def _before_action_hook(self, action: ActionModel) -> None: ...

    async def _after_action_hook(self, action: ActionModel) -> None:
        """Take screenshot after action execution"""

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
            logger.info(f"📸 Stored screenshot filename: {screenshot_filename}")

    def save_agent_actions(self, verbose: bool = False) -> None:
        """
        Saves the agent's traversal data to a JSON file for analysis and replay purposes.

        This function serializes the complete agent session data including all taken actions,
        brain states, browser configuration, and test case information into a structured
        JSON file. The file is saved in a 'traversals' directory with a timestamped filename
        for easy identification and organization.

        Args:
            **verbose** (bool, optional): If True, logs detailed information about each action
                during the saving process. Defaults to False.

        Returns:
            None

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

        # Generate a unique ID for this traversal
        traversal_id = CUID().generate()

        # Get current timestamp in a readable format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save the traversal data with timestamp and unique ID
        traversal_file = traversal_dir / f"traverse_{timestamp}_{traversal_id}.json"

        actions: Dict[str, Any] = {}

        logger.info(f"👉 Number of actions: {len(self.agent_taken_actions)}")
        logger.info(f"🗨️ Number of thoughts: {len(self.agent_brain_states)}")

        for idx, model_taken_action in enumerate(self.agent_taken_actions):

            if verbose:
                logger.info(f"Step {idx + 1}:")
                logger.info("Log:")
                logger.info(model_taken_action)

            # Log screenshot filename if present
            if model_taken_action.screenshot_filename:
                logger.info(
                    f"📸 Action {idx} has screenshot: {model_taken_action.screenshot_filename}"
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

        logger.info(f"Traversal saved with ID: {timestamp}_{traversal_id}")
