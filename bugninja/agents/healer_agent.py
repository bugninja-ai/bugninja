from pathlib import Path
from typing import Any, Dict, List, Optional

from browser_use.agent.views import (  # type: ignore
    AgentOutput,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from cuid2 import Cuid as CUID

from bugninja.agents.bugninja_agent_base import (
    NAVIGATION_IDENTIFIERS,
    BugninjaAgentBase,
)
from bugninja.agents.data_extraction_agent import DataExtractionAgent
from bugninja.prompts.prompt_factory import (
    BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
    HEALDER_AGENT_EXTRA_SYSTEM_PROMPT,
    get_input_schema_prompt,
    get_io_extraction_prompt,
    get_passed_brainstates_related_prompt,
)
from bugninja.schemas.models import BugninjaConfig, FileUploadInfo
from bugninja.schemas.pipeline import BugninjaBrainState, BugninjaExtendedAction
from bugninja.schemas.test_case_io import TestCaseSchema
from bugninja.utils.logging_config import logger
from bugninja.utils.screenshot_manager import ScreenshotManager


class HealerAgent(BugninjaAgentBase):
    """Self-healing agent for browser automation intervention and recovery.

    This agent is specifically designed for **healing interventions** when replay
    operations fail. It extends the base agent functionality with specialized
    capabilities for:
    - automatic error detection and recovery
    - screenshot capture for debugging
    - extended action tracking for healing operations
    - event publishing for healing session monitoring

    The HealerAgent inherits all hooks from `BugninjaAgentBase` and provides
    specialized implementations for healing scenarios.

    Attributes:
        agent_taken_actions (List[BugninjaExtendedAction]): All actions taken during healing
        agent_brain_states (Dict[str, AgentBrain]): Brain states throughout the healing session
        screenshot_manager (ScreenshotManager): Manager for capturing debugging screenshots

    ### Key Methods

    1. *async* **_before_run_hook()** -> `None`: - Initialize healing session and event tracking
    2. *async* **_after_run_hook()** -> `None`: - Complete healing session and event tracking
    3. *async* **_before_step_hook()** -> `None`: - Process actions and create extended actions
    4. *async* **_after_action_hook()** -> `None`: - Capture screenshots after each action
    5. *async* **run()** -> `Optional[AgentHistoryList]`: - Execute healing intervention

    Example:
        ```python
        from bugninja.agents.healer_agent import HealerAgent
        from bugninja.events import EventPublisherManager

        # Create healer agent with event tracking
        healer = HealerAgent(
            task="Fix the broken login flow",
            llm=create_llm_model_from_config(create_llm_config_from_settings()),  # Uses unified LLM configuration
            browser_session=browser_session,
            event_manager=event_manager,
            parent_run_id="original_run_id"
        )

        # Execute healing intervention
        result = await healer.run(max_steps=50)
        ```
    """

    def __init__(  # type:ignore
        self,
        *args,
        task: str,
        bugninja_config: BugninjaConfig,
        parent_run_id: Optional[str] = None,
        extra_instructions: List[str] = [],
        override_system_message: str = BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT,
        extend_system_message: str | None = None,
        already_completed_brainstates: List[BugninjaBrainState] = [],
        output_base_dir: Optional[Path] = None,
        screenshot_manager: Optional[ScreenshotManager] = None,
        io_schema: Optional[TestCaseSchema] = None,
        runtime_inputs: Optional[Dict[str, Any]] = None,
        available_files: Optional[List["FileUploadInfo"]] = None,
        **kwargs,  # type:ignore
    ) -> None:
        """Initialize HealerAgent with healing-specific functionality.

        Args:
            *args: Arguments passed to the parent BugninjaAgentBase class
            task (str): The healing task description for the agent to execute
            parent_run_id (Optional[str]): ID of the parent run for event tracking continuity
            extra_instructions (List[str]): Additional instructions to append to the task
            override_system_message (str): System message to override the default (defaults to navigator prompt)
            extend_system_message (str | None): Additional system message to extend the default
            already_completed_brainstates (List[BugninjaBrainState]): Previously completed brain states for context
            output_base_dir (Optional[Path]): Base directory for all output files (traversals, screenshots, videos)
            io_schema (Optional[TestCaseSchema]): Input/output schema for data extraction and input handling
            runtime_inputs (Optional[Dict[str, Any]]): Input data from dependent tasks to be included in system prompt
            **kwargs: Keyword arguments passed to the parent BugninjaAgentBase class
        """

        # Store unified schema
        self.io_schema = io_schema

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

        task += f"\n\n{get_passed_brainstates_related_prompt(completed_brain_states=already_completed_brainstates)}"

        # Prepare input schema system prompt extension if input data is provided
        input_schema_system_prompt = ""
        if self.io_schema and self.io_schema.input_schema and runtime_inputs:
            input_schema_system_prompt = get_input_schema_prompt(
                self.io_schema.input_schema, runtime_inputs
            )
            if input_schema_system_prompt:
                input_keys = list(self.io_schema.input_schema.keys())
                logger.bugninja_log(
                    f"📥 HealerAgent: Task configured with {len(input_keys)} input data keys: {input_keys}"
                )

        # Prepare available files system prompt extension
        available_files_prompt = ""
        if available_files:
            from bugninja.prompts.prompt_factory import get_available_files_prompt

            available_files_prompt = get_available_files_prompt(available_files)
            if available_files_prompt:
                logger.bugninja_log(
                    f"📎 HealerAgent: Task configured with {len(available_files)} available files"
                )

        system_message_to_extend_by: str = extend_system_message if extend_system_message else ""

        # Combine all system prompt extensions
        extensions = [input_schema_system_prompt, available_files_prompt]
        combined_extensions = "\n\n".join([ext for ext in extensions if ext]).strip()

        if combined_extensions:
            system_message_to_extend_by = (
                f"{system_message_to_extend_by}\n\n{combined_extensions}".strip()
            )

        super().__init__(
            *args,
            bugninja_config=bugninja_config,
            override_system_message=override_system_message,
            extend_system_message=system_message_to_extend_by
            + f"\n\n{HEALDER_AGENT_EXTRA_SYSTEM_PROMPT}",
            extra_instructions=extra_instructions,
            task=task,
            screenshot_manager=screenshot_manager,
            available_files=available_files,
            **kwargs,
        )

        # Store output base directory
        self.output_base_dir = output_base_dir

        # Use parent's run_id if provided, otherwise keep the generated one
        if parent_run_id is not None:
            self.run_id = parent_run_id

    async def _before_run_hook(self) -> None:
        """Initialize healing session with event tracking and screenshot management.

        This hook sets up the healing environment by:
        - initializing screenshot manager for debugging
        - setting up event tracking for healing operations
        - logging the start of the healing intervention
        """
        logger.bugninja_log("🏁 BEFORE-Run hook called")

        # Initialize event tracking for healing run (if event_manager is provided)
        if self.event_manager and self.event_manager.has_publishers():
            try:
                await self.event_manager.initialize_run(
                    run_type="healing",
                    metadata={
                        "task_description": "Healing intervention",
                        "original_task": getattr(self, "task", "Unknown"),
                    },
                    existing_run_id=self.run_id,  # Use existing run_id instead of generating new one
                )
                logger.bugninja_log(f"🎯 Started healing run: {self.run_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize event tracking: {e}")

    # ? we do not need to override the _after_run_hook for the healer agent
    async def _after_run_hook(self) -> None:
        """Complete event tracking for healing run.

        This hook finalizes the event tracking for healing interventions,
        marking the run as completed or failed based on the final result.

        The hook:
        - checks for successful completion of healing operations
        - publishes final run status to event managers
        - logs completion status for monitoring
        """
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

        # Complete event tracking for healing run
        if self.event_manager and self.run_id:
            try:
                if not self.state.last_result:
                    raise Exception("No results found for healing run")

                success = not any(
                    result.error for result in self.state.last_result if hasattr(result, "error")
                )
                await self.event_manager.complete_run(self.run_id, success)
                logger.bugninja_log(f"✅ Completed healing run: {self.run_id}")

            except Exception as e:
                logger.warning(f"Failed to complete event tracking: {e}")

    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """Process actions and create extended actions for healing operations.

        This hook is called before each step in the healing process and:
        - creates brain state tracking for the current step
        - generates extended actions with DOM element information
        - associates actions with their extended versions
        - stores actions for later analysis and debugging

        Args:
            browser_state_summary (BrowserStateSummary): Current browser state information
            model_output (AgentOutput): Model output containing actions to be executed
        """
        logger.bugninja_log("🪝 BEFORE-Step hook called")

        # ? we create the brain state here since a single thought can belong to multiple actions
        brain_state_id: str = CUID().generate()
        self.agent_brain_states[brain_state_id] = model_output.current_state

        current_page: Page = await self.browser_session.get_current_page()

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

        # ? we take screenshot of `go_to_url` action after it happens since before it the page is not loaded yet
        if extended_action.get_action_type() in NAVIGATION_IDENTIFIERS:
            #! taking appropriate screenshot before each action
            await self.handle_taking_screenshot_for_action(extended_action=extended_action)

        # ? adding the taken action to the list of agent actions
        self.agent_taken_actions.append(self.current_step_extended_actions[action_idx_in_step])
