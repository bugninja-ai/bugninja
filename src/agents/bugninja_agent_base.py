import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from browser_use.agent.message_manager.utils import save_conversation  # type: ignore
from browser_use.agent.service import (  # type: ignore
    Agent,
    AgentStepInfo,
    logger,
)
from browser_use.agent.views import (  # type: ignore
    ActionResult,
    AgentHistoryList,
    AgentOutput,
    StepMetadata,
)
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.controller.registry.views import ActionModel  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from langchain_core.messages import HumanMessage


def hook_missing_error(hook_name: str, class_val: type) -> NotImplementedError:
    return NotImplementedError(f"The '{hook_name}' is not implemented for '{class_val.__name__}'!")


class BugninjaAgentBase(Agent, ABC):

    @staticmethod
    async def get_raw_html_of_playwright_page(page: Page) -> str:
        # current_page: Page = await self.browser_session.get_current_page()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("load")
        html_content_of_page: str = await page.content()
        return html_content_of_page

    @abstractmethod
    async def _before_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """A hook that is called BEFORE a step is taken, but the agent already has model output regarding the actions to be taken!
        A step is representing a specific element of the workflow; a single step represents a workflow element regarding achievement of the goal of the agent.
        What is considered a step is up to the agent to decide.

        **KEEP IN MIND**: A single step can have multiple actions

        Args:
            browser_state_summary (BrowserStateSummary): The BrowserStateSummary of the current step
            model_output (AgentOutput): The output of the agent representing the actions to be taken

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_before_step_hook", self.__class__)

    @abstractmethod
    async def _after_step_hook(
        self,
        browser_state_summary: BrowserStateSummary,
        model_output: AgentOutput,
    ) -> None:
        """A hook that is called AFTER a step is taken with all of it's actions!
        A step is representing a specific element of the workflow; a single step represents a workflow element regarding achievement of the goal of the agent.
        What is considered a step is up to the agent to decide.

        **KEEP IN MIND**: A single step can have multiple actions

        Args:
            browser_state_summary (BrowserStateSummary): The BrowserStateSummary of the current step
            model_output (AgentOutput): The output of the agent representing the action that was taken

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_after_step_hook", self.__class__)

    @abstractmethod
    async def _before_run_hook(self) -> None:
        """A hook that is called BEFORE the agent starts running.
        Ideal for any initialization that needs to be done before the agent starts running.

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_before_run_hook", self.__class__)

    @abstractmethod
    async def _after_run_hook(self) -> None:
        """A hook that is called AFTER the agent is done running.
        Ideal for any cleanup that needs to be done after the agent is done running, or saving any sort of data

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_after_run_hook", self.__class__)

    @abstractmethod
    async def _before_action_hook(self, action: ActionModel) -> None:
        """A hook that is called BEFORE a single action is taken by the agent

        Args:
            action (ActionModel): The action that is about to be taken

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_before_action_hook", self.__class__)

    @abstractmethod
    async def _after_action_hook(self, action: ActionModel) -> None:
        """A hook that is called AFTER a single action was taken by the agent.

        Args:
            action (ActionModel): The action that was taken

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise hook_missing_error("_after_action_hook", self.__class__)

    @time_execution_async("--run (agent)")
    async def run(self, max_steps: int = 100) -> Optional[AgentHistoryList]:
        """Execute the task with maximum number of steps"""

        await self._before_run_hook()
        results = await super().run(max_steps=max_steps, on_step_start=None, on_step_end=None)
        await self._after_run_hook()
        return results

    @time_execution_async("--step (agent)")
    async def step(self, step_info: AgentStepInfo | None = None) -> None:
        """Execute one step of the task"""
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
                logger.info(f"📄 Result: {result[-1].extracted_content}")
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
            if not result:
                return
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
        """Execute multiple actions"""
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

                await self._before_action_hook(action=action)

                result = await self.controller.act(
                    action=action,
                    browser_session=self.browser_session,
                    page_extraction_llm=self.settings.page_extraction_llm,
                    sensitive_data=self.sensitive_data,
                    available_file_paths=self.settings.available_file_paths,
                    context=self.context,
                )

                await self._after_action_hook(action=action)

                results.append(result)

                # Get action name from the action model
                action_data = action.model_dump(exclude_unset=True)
                action_name = next(iter(action_data.keys())) if action_data else "unknown"
                logger.info(f"☑️ Executed action {i + 1}/{len(actions)}: {action_name}")
                if results[-1].is_done or results[-1].error or i == len(actions) - 1:
                    break

                await asyncio.sleep(self.browser_profile.wait_between_actions)
                # hash all elements. if it is a subset of cached_state its fine - else break (new elements on page)

            except asyncio.CancelledError:
                # Gracefully handle task cancellation
                logger.info(f"Action {i + 1} was cancelled due to Ctrl+C")
                if not results:
                    # Add a result for the cancelled action
                    results.append(
                        ActionResult(
                            error="The action was cancelled due to Ctrl+C", include_in_memory=True
                        )
                    )
                raise InterruptedError("Action cancelled by user")

        return results
