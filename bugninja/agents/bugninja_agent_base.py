import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from browser_use.agent.message_manager.utils import save_conversation  # type: ignore
from browser_use.agent.service import (  # type: ignore
    Agent,
    AgentStepInfo,
)
from browser_use.agent.views import (  # type: ignore
    ActionResult,
    AgentBrain,
    AgentHistoryList,
    AgentOutput,
    StepMetadata,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from cuid2 import Cuid as CUID
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from bugninja.agents.extensions import BugninjaController
from bugninja.config import (
    create_llm_model_from_config,
    create_provider_model_from_settings,
)
from bugninja.config.llm_config import LLMConfig
from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.events import EventPublisherManager
from bugninja.prompts.prompt_factory import get_extra_instructions_related_prompt
from bugninja.schemas.models import BugninjaConfig
from bugninja.schemas.pipeline import BugninjaExtendedAction
from bugninja.utils.logging_config import logger
from bugninja.utils.screenshot_manager import ScreenshotManager
from bugninja.utils.selector_factory import SelectorFactory
from bugninja.utils.video_recording_manager import VideoRecordingManager


def hook_missing_error(hook_name: str, class_val: type) -> NotImplementedError:
    """Generate a standardized error for missing hook implementations.

    Args:
        hook_name (str): Name of the missing hook method
        class_val (type): Class that is missing the hook implementation

    Returns:
        NotImplementedError: Standardized error message for missing hooks
    """
    return NotImplementedError(f"The '{hook_name}' is not implemented for '{class_val.__name__}'!")


SELECTOR_ORIENTED_ACTIONS: List[str] = [
    "click_element_by_index",
    "input_text",
    "get_dropdown_options",
    "select_dropdown_option",
    "drag_drop",
]

ALTERNATIVE_XPATH_SELECTORS_KEY: str = "alternative_relative_xpaths"
DOM_ELEMENT_DATA_KEY: str = "dom_element_data"
BRAINSTATE_IDX_DATA_KEY: str = "idx_in_brainstate"

GO_TO_URL_IDENTIFIER: str = "go_to_url"


class BugninjaAgentBase(Agent, ABC):
    """Base class for all Bugninja agents with extended functionality.

    This class provides **common functionality** for all Bugninja agents including:
    - extended action tracking and management
    - event publishing capabilities
    - screenshot management
    - comprehensive hook system for customization

    It extends the base `Agent` class with Bugninja-specific features while maintaining
    compatibility with the underlying browser-use framework.

    Attributes:
        _action_to_extended_index (Dict[int, int]): Mapping between actions and their extended indices
        run_id (str): Unique identifier for the current run
        event_manager (Optional[EventPublisherManager]): Event publisher manager for tracking operations

    ### Key Methods

    1. *async* **run()** -> `Optional[AgentHistoryList]`: - Execute the agent with maximum steps
    2. *async* **step()** -> `None`: - Execute one step of the task
    3. *async* **multi_act()** -> `List[ActionResult]`: - Execute multiple actions
    4. *abstract* **_before_step_hook()** -> `None`: - Hook called before each step
    5. *abstract* **_after_step_hook()** -> `None`: - Hook called after each step
    6. *abstract* **_before_run_hook()** -> `None`: - Hook called before run starts
    7. *abstract* **_after_run_hook()** -> `None`: - Hook called after run completes
    8. *abstract* **_before_action_hook()** -> `None`: - Hook called before each action
    9. *abstract* **_after_action_hook()** -> `None`: - Hook called after each action

    Example:
        ```python
        from bugninja.agents.bugninja_agent_base import BugninjaAgentBase
        from browser_use.agent.views import AgentOutput
        from browser_use.browser.views import BrowserStateSummary

        class CustomAgent(BugninjaAgentBase):
            async def _before_step_hook(self, browser_state_summary: BrowserStateSummary,
                                      model_output: AgentOutput) -> None:
                # Custom logic before each step
                pass

            async def _after_step_hook(self, browser_state_summary: BrowserStateSummary,
                                     model_output: AgentOutput) -> None:
                # Custom logic after each step
                pass

            # Implement other abstract methods...
        ```
    """

    def __init__(  # type:ignore
        self,
        *args,
        task: str,
        bugninja_config: BugninjaConfig,
        run_id: Optional[str] = None,
        extra_instructions: List[str] = [],
        override_system_message: str | None = None,
        extend_system_message: str | None = None,
        video_recording_config: Optional[VideoRecordingConfig] = None,
        output_base_dir: Optional[Path] = None,
        screenshot_manager: Optional[ScreenshotManager] = None,
        cli_mode: bool = False,
        **kwargs,  # type:ignore
    ) -> None:
        """Initialize BugninjaAgentBase with extended functionality.

        Args:
            *args: Arguments passed to the parent Agent class
            task (str): The task description for the agent to execute
            run_id (Optional[str]): Unique identifier for the current run. If None, generates a new CUID
            extra_instructions (List[str]): Additional instructions to append to the task
            override_system_message (str | None): System message to override the default
            extend_system_message (str | None): Additional system message to extend the default
            video_recording_config (Optional[VideoRecordingConfig]): Video recording configuration
            output_base_dir (Optional[Path]): Base directory for all output files (traversals, screenshots, videos)
            screenshot_manager (Optional[ScreenshotManager]): Screenshot manager instance
            cli_mode (bool): Whether running in CLI mode (prevents automatic directory creation)
            **kwargs: Keyword arguments passed to the parent Agent class
        """
        self.raw_task: str = task
        self.extra_instructions = extra_instructions
        self.video_recording_config = video_recording_config
        self.bugninja_config = bugninja_config

        if extra_instructions:
            extra_instructions_prompt: str = get_extra_instructions_related_prompt(
                extra_instruction_list=extra_instructions
            )
            task += f"\n\n{extra_instructions_prompt}"

        custom_controller = BugninjaController()

        super().__init__(*args, **kwargs, task=task, controller=custom_controller)
        # Initialize extended actions storage
        self.current_step_extended_actions: List["BugninjaExtendedAction"] = []
        self._action_to_extended_index: Dict[int, int] = {}

        # Generate run_id at creation time for consistency across all agents
        self.run_id: str = CUID().generate()

        if run_id is not None:
            self.run_id = run_id

        # Initialize event publisher manager (explicitly passed)
        self.event_manager: Optional[EventPublisherManager] = None

        # Initialize video recording manager if enabled
        self.video_recording_manager: Optional[VideoRecordingManager] = (
            # TODO! temporal disable
            # VideoRecordingManager(self.run_id, video_recording_config)
            # if video_recording_config
            None
        )

        self.output_base_dir: Optional[Path] = output_base_dir

        self.screenshot_manager = (
            screenshot_manager
            if screenshot_manager
            else ScreenshotManager(
                run_id=self.run_id, base_dir=self.output_base_dir, cli_mode=cli_mode
            )
        )

        self.agent_taken_actions: List[BugninjaExtendedAction] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

    async def handle_taking_screenshot_for_action(
        self, extended_action: BugninjaExtendedAction
    ) -> None:
        await self.browser_session.remove_highlights()

        current_page: Page = await self.browser_session.get_current_page()

        await self.wait_proper_load_state(current_page)
        # Take screenshot and get filename
        screenshot_filename = await self.screenshot_manager.take_screenshot(
            current_page,  # type: ignore
            extended_action,
            self.browser_session,
        )

        extended_action.screenshot_filename = screenshot_filename

    def _create_llm(
        self,
        llm_config: Optional[LLMConfig] = None,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        """Create LLM model using unified configuration.

        This method provides a centralized way for all agents to create LLM instances.
        It uses the unified LLM configuration system for consistent model creation.

        Args:
            llm_config (Optional[LLMConfig]): Unified LLM configuration
            temperature (Optional[float]): Temperature setting (overrides config)

        Returns:
            BaseChatModel: Configured LLM model instance

        Raises:
            ValueError: If LLM configuration is invalid or missing
        """
        try:

            # Use provided LLM config or create from settings
            if llm_config is not None:

                config = llm_config
                if temperature is not None:
                    config.temperature = temperature
                return create_llm_model_from_config(config)
            else:
                return create_provider_model_from_settings(temperature)
        except Exception as e:
            raise ValueError(f"Failed to create LLM model: {e}")

    @staticmethod
    async def wait_proper_load_state(page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("load")

    @staticmethod
    async def get_raw_html_of_playwright_page(page: Page) -> str:
        """Get the raw HTML content of a Playwright page.

        Args:
            page (Page): Playwright page object

        Returns:
            str: Raw HTML content of the page
        """
        await BugninjaAgentBase.wait_proper_load_state(page)
        html_content_of_page: str = await page.content()
        return html_content_of_page

    async def _get_current_url(self) -> str:
        """Get the current URL for event publishing.

        Returns:
            str: The current page URL as a string, or "unknown" if not available
        """
        try:
            if hasattr(self, "browser_session") and self.browser_session:
                current_page = await self.browser_session.get_current_page()
                url = current_page.url
                if isinstance(url, str):
                    return url
        except Exception:
            pass
        return "unknown"

    async def _publish_action_event(
        self,
        brain_state_id: str,
        actual_brain_state: AgentBrain,
        action_result_data: BugninjaExtendedAction,
    ) -> None:
        if not self.event_manager or not self.run_id:
            return

        try:
            await self.event_manager.publish_action_event(
                run_id=self.run_id,
                brain_state_id=brain_state_id,
                actual_brain_state=actual_brain_state,
                action_result_data=action_result_data,
            )
        except Exception:
            # Continue execution even if event publishing fails
            pass

    @abstractmethod
    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """Hook called BEFORE a step is taken, but after model output is generated.

        A step represents a specific element of the workflow; a single step represents
        a workflow element regarding achievement of the goal of the agent. What is
        considered a step is up to the agent to decide.

        **KEEP IN MIND**: A single step can have multiple actions

        Args:
            browser_state_summary (BrowserStateSummary): The browser state summary of the current step
            model_output (AgentOutput): The output of the agent representing the actions to be taken

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_before_step_hook", self.__class__)

    @abstractmethod
    async def _after_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """Hook called AFTER a step is taken with all of its actions.

        A step represents a specific element of the workflow; a single step represents
        a workflow element regarding achievement of the goal of the agent. What is
        considered a step is up to the agent to decide.

        **KEEP IN MIND**: A single step can have multiple actions

        Args:
            browser_state_summary (BrowserStateSummary): The browser state summary of the current step
            model_output (AgentOutput): The output of the agent representing the actions taken

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_after_step_hook", self.__class__)

    @abstractmethod
    async def _before_run_hook(self) -> None:
        """Hook called BEFORE a run is started.

        This hook is called at the beginning of the agent execution, before any
        steps or actions are taken.

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_before_run_hook", self.__class__)

    @abstractmethod
    async def _after_run_hook(self) -> None:
        """Hook called AFTER a run is finished.

        This hook is called at the end of the agent execution, after all steps
        and actions have been completed.

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_after_run_hook", self.__class__)

    @abstractmethod
    async def _before_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Hook called BEFORE an action is taken.

        Args:
            action (ActionModel): The action that is about to be taken

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_before_action_hook", self.__class__)

    @abstractmethod
    async def _after_action_hook(
        self,
        action_idx_in_step: int,
        action: ActionModel,
    ) -> None:
        """Hook called AFTER an action is taken.

        Args:
            action (ActionModel): The action that was just taken

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise hook_missing_error("_after_action_hook", self.__class__)

    def _find_matching_extended_action(self, action: ActionModel) -> "BugninjaExtendedAction":
        """Find the matching extended action for a given action.

        Args:
            action (ActionModel): The action to find the extended version for

        Returns:
            BugninjaExtendedAction: The matching extended action
        """
        action_index: int = self._action_to_extended_index.get(id(action), None)  # type: ignore
        return self.current_step_extended_actions[action_index]

    def _associate_action_with_extended_action(self, action: ActionModel, index: int) -> None:
        """Associate an action with its extended action index.

        Args:
            action (ActionModel): The action to associate
            index (int): The index of the extended action
        """
        self._action_to_extended_index[id(action)] = index

    def _clear_action_mapping(self) -> None:
        """Clear the action mapping to prevent memory accumulation."""
        self._action_to_extended_index.clear()

    @time_execution_async("--run (agent)")
    async def run(self, max_steps: int = 100) -> Optional[AgentHistoryList]:
        """Execute the task with maximum number of steps.

        Args:
            max_steps (int): Maximum number of steps to execute

        Returns:
            Optional[AgentHistoryList]: The execution history, or None if execution fails
        """
        await self._before_run_hook()
        results = await super().run(max_steps=max_steps, on_step_start=None, on_step_end=None)
        await self._after_run_hook()

        return results

    @time_execution_async("--step (agent)")
    async def step(self, step_info: AgentStepInfo | None = None) -> None:
        """Execute one step of the task.

        This method orchestrates the execution of a single step, including:
        - browser state analysis
        - model output generation
        - action execution
        - event publishing
        - hook management

        Args:
            step_info (AgentStepInfo | None): Information about the current step
        """
        browser_state_summary = None
        model_output = None
        result: List[ActionResult] = []
        step_start_time = time.time()
        tokens = 0

        try:
            browser_state_summary = await self.browser_session.get_state_summary(
                cache_clickable_elements_hashes=True
            )
            current_page = await self.browser_session.get_current_page()
            self._log_step_context(current_page, browser_state_summary)
            # generate procedural memory if needed
            if (
                self.enable_memory
                and self.memory
                and self.state.n_steps % self.memory.config.memory_interval == 0
            ):
                self.memory.create_procedural_memory(self.state.n_steps)
            await self._raise_if_stopped_or_paused()
            # Update action models with page-specific actions
            await self._update_action_models_for_page(current_page)
            # Get page-specific filtered actions
            page_filtered_actions = self.controller.registry.get_prompt_description(current_page)
            # If there are page-specific actions, add them as a special message for this step only
            if page_filtered_actions:
                page_action_message = f"For this page, these additional actions are available:\n{page_filtered_actions}"
                self._message_manager._add_message_with_tokens(
                    HumanMessage(content=page_action_message)
                )
            # If using raw tool calling method, we need to update the message context with new actions
            if self.tool_calling_method == "raw":
                # For raw tool calling, get all non-filtered actions plus the page-filtered ones
                all_unfiltered_actions = self.controller.registry.get_prompt_description()
                all_actions = all_unfiltered_actions
                if page_filtered_actions:
                    all_actions += "\n" + page_filtered_actions
                context_lines = (self._message_manager.settings.message_context or "").split("\n")
                non_action_lines = [
                    line for line in context_lines if not line.startswith("Available actions:")
                ]
                updated_context = "\n".join(non_action_lines)
                if updated_context:
                    updated_context += f"\n\nAvailable actions: {all_actions}"
                else:
                    updated_context = f"Available actions: {all_actions}"
                self._message_manager.settings.message_context = updated_context
            self._message_manager.add_state_message(
                browser_state_summary=browser_state_summary,
                result=self.state.last_result,
                step_info=step_info,
                use_vision=self.settings.use_vision,
            )
            # Run planner at specified intervals if planner is configured
            if (
                self.settings.planner_llm
                and self.state.n_steps % self.settings.planner_interval == 0
            ):
                plan = await self._run_planner()
                # add plan before last state message
                self._message_manager.add_plan(plan, position=-1)

            if step_info and step_info.is_last_step():
                # Add last step warning if needed
                msg = 'Now comes your last step. Use only the "done" action now. No other actions - so here your action sequence must have length 1.'
                msg += '\nIf the task is not yet fully finished as requested by the user, set success in "done" to false! E.g. if not all steps are fully completed.'
                msg += '\nIf the task is fully finished, set success in "done" to true.'
                msg += "\nInclude everything you found out for the ultimate task in the done text."
                logger.info("Last step finishing up")
                self._message_manager._add_message_with_tokens(HumanMessage(content=msg))

                self.AgentOutput = self.DoneAgentOutput
            input_messages = self._message_manager.get_messages()
            tokens = self._message_manager.state.history.current_tokens
            try:
                model_output = await self.get_next_action(input_messages)

                if (
                    not model_output.action
                    or not isinstance(model_output.action, list)
                    or all(action.model_dump() == {} for action in model_output.action)
                ):
                    logger.warning("Model returned empty action. Retrying...")
                    clarification_message = HumanMessage(
                        content="You forgot to return an action. Please respond only with a valid JSON action according to the expected format."
                    )
                    retry_messages = input_messages + [clarification_message]
                    model_output = await self.get_next_action(retry_messages)
                    if not model_output.action or all(
                        action.model_dump() == {} for action in model_output.action
                    ):
                        logger.warning(
                            "Model still returned empty after retry. Inserting safe noop action."
                        )
                        action_instance = self.ActionModel(
                            done={
                                "success": False,
                                "text": "No next action returned by LLM!",
                            }
                        )
                        model_output.action = [action_instance]
                # Check again for paused/stopped state after getting model output
                await self._raise_if_stopped_or_paused()
                self.state.n_steps += 1
                if self.register_new_step_callback:
                    if inspect.iscoroutinefunction(self.register_new_step_callback):
                        await self.register_new_step_callback(
                            browser_state_summary, model_output, self.state.n_steps
                        )
                    else:
                        self.register_new_step_callback(
                            browser_state_summary, model_output, self.state.n_steps
                        )
                if self.settings.save_conversation_path:
                    target = self.settings.save_conversation_path + f"_{self.state.n_steps}.txt"
                    save_conversation(
                        input_messages,
                        model_output,
                        target,
                        self.settings.save_conversation_path_encoding,
                    )
                self._message_manager._remove_last_state_message()  # we dont want the whole state in the chat history
                # check again if Ctrl+C was pressed before we commit the output to history
                await self._raise_if_stopped_or_paused()
                self._message_manager.add_model_output(model_output)

            except asyncio.CancelledError:
                # Task was cancelled due to Ctrl+C
                self._message_manager._remove_last_state_message()
                raise InterruptedError("Model query cancelled by user")
            except InterruptedError:
                # Agent was paused during get_next_action
                self._message_manager._remove_last_state_message()
                raise  # Re-raise to be caught by the outer try/except
            except Exception as e:
                # model call failed, remove last state message from history
                self._message_manager._remove_last_state_message()
                raise e

            await self._before_step_hook(
                browser_state_summary=browser_state_summary, model_output=model_output
            )

            result = await self.multi_act(model_output.action)
            self.state.last_result = result

            if len(result) > 0 and result[-1].is_done:
                logger.bugninja_log(f"📄 Result: {result[-1].extracted_content}")
            self.state.consecutive_failures = 0

            await self._after_step_hook(
                browser_state_summary=browser_state_summary, model_output=model_output
            )

        except InterruptedError:
            # logger.debug('Agent paused')
            self.state.last_result = [
                ActionResult(
                    error="The agent was paused mid-step - the last action might need to be repeated",
                    include_in_memory=False,
                )
            ]
            return
        except asyncio.CancelledError:
            # Directly handle the case where the step is cancelled at a higher level
            # logger.debug('Task cancelled - agent was paused with Ctrl+C')
            self.state.last_result = [
                ActionResult(error="The agent was paused with Ctrl+C", include_in_memory=False)
            ]
            raise InterruptedError("Step cancelled by user")
        except Exception as e:
            result = await self._handle_step_error(e)
            self.state.last_result = result
        finally:
            step_end_time = time.time()
            if result:
                if browser_state_summary:
                    metadata = StepMetadata(
                        step_number=self.state.n_steps,
                        step_start_time=step_start_time,
                        step_end_time=step_end_time,
                        input_tokens=tokens,
                    )
                    self._make_history_item(model_output, browser_state_summary, result, metadata)
                # Log step completion summary
                self._log_step_completion_summary(step_start_time, result)

    @time_execution_async("--multi_act")
    async def multi_act(
        self,
        actions: list[ActionModel],
        check_for_new_elements: bool = True,
    ) -> list[ActionResult]:
        """Execute multiple actions with comprehensive error handling.

        This method executes a sequence of actions while handling:
        - element index changes after page modifications
        - new element detection
        - action cancellation
        - event publishing
        - extended action tracking

        Args:
            actions (list[ActionModel]): List of actions to execute
            check_for_new_elements (bool): Whether to check for new elements between actions

        Returns:
            list[ActionResult]: Results of all executed actions
        """
        results: list[ActionResult] = []

        cached_selector_map = await self.browser_session.get_selector_map()
        cached_path_hashes = {e.hash.branch_path_hash for e in cached_selector_map.values()}

        await self.browser_session.remove_highlights()

        for i, action in enumerate(actions):
            if action.get_index() is not None and i != 0:
                new_browser_state_summary = await self.browser_session.get_state_summary(
                    cache_clickable_elements_hashes=False
                )
                new_selector_map = new_browser_state_summary.selector_map

                # Detect index change after previous action
                orig_target = cached_selector_map.get(action.get_index())  # type: ignore
                orig_target_hash = orig_target.hash.branch_path_hash if orig_target else None
                new_target = new_selector_map.get(action.get_index())  # type: ignore
                new_target_hash = new_target.hash.branch_path_hash if new_target else None
                if orig_target_hash != new_target_hash:
                    msg = f"Element index changed after action {i} / {len(actions)}, because page changed."
                    logger.info(msg)
                    results.append(ActionResult(extracted_content=msg, include_in_memory=True))
                    break

                new_path_hashes = {e.hash.branch_path_hash for e in new_selector_map.values()}
                if check_for_new_elements and not new_path_hashes.issubset(cached_path_hashes):
                    # next action requires index but there are new elements on the page
                    msg = f"Something new appeared after action {i} / {len(actions)}"
                    logger.info(msg)
                    results.append(ActionResult(extracted_content=msg, include_in_memory=True))
                    break

            try:
                await self._raise_if_stopped_or_paused()

                await self._before_action_hook(action_idx_in_step=i, action=action)

                result = await self.controller.act(
                    action=action,
                    browser_session=self.browser_session,
                    page_extraction_llm=self.settings.page_extraction_llm,
                    sensitive_data=self.sensitive_data,
                    available_file_paths=self.settings.available_file_paths,
                    context=self.context,
                )

                await self._after_action_hook(action_idx_in_step=i, action=action)

                results.append(result)

                # Get action name from the action model
                action_data = action.model_dump(exclude_unset=True)
                action_name = next(iter(action_data.keys())) if action_data else "unknown"
                logger.bugninja_log(f"☑️ Executed action {i + 1}/{len(actions)}: {action_name}")

                # Associate action with extended action
                self._associate_action_with_extended_action(action, i)

                brain_state_id: str
                brain_state: AgentBrain
                brain_state_id, brain_state = list(self.agent_brain_states.items())[-1]

                # Publish action completion event
                if self.event_manager and self.run_id:
                    await self._publish_action_event(
                        brain_state_id=brain_state_id,
                        actual_brain_state=brain_state,
                        action_result_data=self.current_step_extended_actions[i],
                    )

                if results[-1].is_done or results[-1].error or i == len(actions) - 1:
                    break

                await asyncio.sleep(self.browser_session.browser_profile.wait_between_actions)
                # hash all elements. if it is a subset of cached_state its fine - else break (new elements on page)

            except asyncio.CancelledError:
                # Gracefully handle task cancellation
                logger.bugninja_log(f"Action {i + 1} was cancelled due to Ctrl+C")
                if not results:
                    # Add a result for the cancelled action
                    results.append(
                        ActionResult(
                            error="The action was cancelled due to Ctrl+C", include_in_memory=True
                        )
                    )
                raise InterruptedError("Action cancelled by user")

        return results

    @staticmethod
    async def extend_action_model(
        brain_state_id: str,
        action_idx: int,
        current_page: Page,
        browser_state_summary: BrowserStateSummary,
        action: ActionModel,
    ) -> BugninjaExtendedAction:
        short_action_descriptor: Dict[str, Any] = action.model_dump(exclude_none=True)
        logger.bugninja_log(f"📄 Action: {short_action_descriptor}")

        bugninja_action = BugninjaExtendedAction.model_validate(
            {
                "brain_state_id": brain_state_id,
                "action": action.model_dump(),
                "idx_in_brainstate": action_idx,
                DOM_ELEMENT_DATA_KEY: None,
            }
        )

        action_key: str = list(short_action_descriptor.keys())[-1]

        #!! these values here were selected by hand, if necessary they can be extended with other actions as well
        if action_key in SELECTOR_ORIENTED_ACTIONS:
            selector_data: Dict[str, Any] = browser_state_summary.selector_map[
                short_action_descriptor[action_key]["index"]
            ].__json__()

            formatted_xpath: str = "//" + selector_data["xpath"].strip("/")
            #! adding the raw XPath to the short action descriptor (even though it is not part of the model output)
            short_action_descriptor[action_key]["xpath"] = formatted_xpath
            logger.bugninja_log(f"📄 {action_key} on {formatted_xpath}")

            bugninja_action.dom_element_data = await BugninjaAgentBase.__extend_action_with_data(
                selector_data=selector_data,
                formatted_xpath=formatted_xpath,
                current_page=current_page,
            )

        return bugninja_action

    @staticmethod
    async def __extend_action_with_data(
        selector_data: Dict[str, Any], formatted_xpath: str, current_page: Page
    ) -> Dict[str, Any]:

        #! here we only want to keep the first layer of children for specific element in order to avoid unnecessarily large data dump in JSON
        ch: Dict[str, Any]

        if "children" in selector_data:
            sanitised_children: List[Dict[str, Any]] = []
            for ch in selector_data["children"]:
                ch["children"] = []
                sanitised_children.append(ch)
            selector_data["children"] = sanitised_children

        current_page_html: str = await BugninjaAgentBase.get_raw_html_of_playwright_page(
            page=current_page
        )

        selector_data[ALTERNATIVE_XPATH_SELECTORS_KEY] = SelectorFactory(
            html_content=current_page_html
        ).generate_relative_xpaths_from_full_xpath(full_xpath=formatted_xpath)

        return selector_data

    @staticmethod
    async def extend_model_output_with_info(
        brain_state_id: str,
        current_page: Page,
        model_output: AgentOutput,
        browser_state_summary: BrowserStateSummary,
    ) -> List["BugninjaExtendedAction"]:
        """Extend agent actions with additional DOM element information and alternative selectors.

        This function processes agent actions and enriches them with detailed DOM element data,
        including XPath selectors and alternative relative XPath selectors for selector-oriented
        actions. It's designed to enhance action tracking and debugging capabilities by providing
        comprehensive element identification information.

        Args:
            brain_state_id (str): Unique identifier for the current brain state/agent session
            current_page (Page): Playwright page object representing the current browser page
            model_output (AgentOutput): The output from the agent model containing actions to be processed
            browser_state_summary (BrowserStateSummary): Summary of the current browser state including selector mappings

        Returns:
            List[BugninjaExtendedAction]: List of extended actions with enriched DOM element data

        Raises:
            Exception: Propagates any exceptions from SelectorFactory operations

        Notes:
            - Only selector-oriented actions (defined in SELECTOR_ORIENTED_ACTIONS) are enriched with DOM element data
            - For selector-oriented actions, the function:
            1. Extracts the element index from the action
            2. Retrieves the corresponding DOM element from browser_state_summary
            3. Formats the XPath selector
            4. Generates alternative relative XPath selectors using SelectorFactory
            5. Adds all this data to the action dictionary
            - Non-selector-oriented actions are included in the result but without DOM element data
            - The function handles exceptions during selector generation gracefully, setting alternative selectors to None if generation fails
        """
        return [
            await BugninjaAgentBase.extend_action_model(
                brain_state_id=brain_state_id,
                action_idx=action_idx,
                current_page=current_page,
                action=action,
                browser_state_summary=browser_state_summary,
            )
            for action_idx, action in enumerate(model_output.action)
        ]
