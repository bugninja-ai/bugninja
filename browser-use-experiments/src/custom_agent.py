import asyncio
import inspect
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

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
    DOMElementNode,
    StepMetadata,
)
from browser_use.browser.profile import ViewportSize  # type: ignore
from browser_use.browser.session import Page  # type: ignore
from browser_use.browser.views import BrowserStateSummary  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from cuid2 import Cuid as CUID
from langchain_core.messages import HumanMessage
from rich import print as rich_print

from src.selector_factory import SelectorFactory

AgentHookFunc = Callable[["Agent"], Awaitable[None]]


class QuinoAgent(Agent):

    async def get_raw_html_of_current_page(self) -> str:
        current_page: Page = await self.browser_session.get_current_page()
        await current_page.wait_for_load_state("domcontentloaded")
        await current_page.wait_for_load_state("load")
        html_content_of_page: str = await current_page.content()
        return html_content_of_page

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

            #! generating the alternative CSS and XPath selectors should happen BEFORE the actions are completed
            await self.extract_information_from_step(
                model_output=model_output, browser_state_summary=browser_state_summary
            )

            result = await self.multi_act(model_output.action)
            self.state.last_result = result

            if len(result) > 0 and result[-1].is_done:
                logger.info(f"📄 Result: {result[-1].extracted_content}")
            self.state.consecutive_failures = 0
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

    @time_execution_async("--run (agent)")
    async def run(
        self,
        max_steps: int = 100,
        on_step_start: AgentHookFunc | None = None,
        on_step_end: AgentHookFunc | None = None,
    ) -> Optional[AgentHistoryList]:
        """Execute the task with maximum number of steps"""

        self.agent_taken_actions: List[Dict[str, Any]] = []

        results = await super().run(
            max_steps=max_steps, on_step_start=on_step_start, on_step_end=on_step_end
        )

        self.save_q_agent_actions()

        return results

    async def extract_information_from_step(
        self, model_output: AgentOutput = None, browser_state_summary: BrowserStateSummary = None
    ) -> None:
        for action in model_output.action:
            short_action_descriptor: Dict[str, Any] = action.model_dump(exclude_none=True)

            action_dictionary: Dict[str, Any] = {
                "action": action.model_dump(),
                "dom_element_data": None,
            }

            logger.info(f"📄 Action: {short_action_descriptor}")

            action_key: str = list(short_action_descriptor.keys())[-1]

            logger.info(f"📄 Action key: {action_key}")

            #!! these values here were selected by hand, if necessary they can be extended with other actions as well
            if action_key in [
                "click_element_by_index",
                "input_text",
                "get_dropdown_options",
                "select_dropdown_option",
                "drag_drop",
            ]:
                action_index = short_action_descriptor[action_key]["index"]
                chosen_selector: DOMElementNode = browser_state_summary.selector_map[action_index]
                logger.info(f"📄 {action_key} on {chosen_selector}")

                selector_data: Dict[str, Any] = chosen_selector.__json__()

                formatted_xpath: str = "//" + selector_data["xpath"].strip("/")
                rich_print(selector_data["xpath"])
                rich_print(formatted_xpath)

                #! adding the raw XPath to the short action descriptor (even though it is not part of the model output)
                short_action_descriptor[action_key]["xpath"] = formatted_xpath

                raw_html: str = await self.get_raw_html_of_current_page()

                try:
                    factory = SelectorFactory(raw_html)
                    selector_data["alternative_relative_xpaths"] = (
                        factory.generate_relative_xpaths_from_full_xpath(full_xpath=formatted_xpath)
                    )

                except Exception as e:
                    logger.error(f"Error generating alternative selectors: {e}")
                    selector_data["alternative_relative_xpaths"] = None

                action_dictionary["dom_element_data"] = selector_data

            self.agent_taken_actions.append(action_dictionary)

    def save_q_agent_actions(self, verbose: bool = False) -> None:

        viewport: Optional[ViewportSize] = self.browser_profile.viewport
        viewport_element: Optional[Dict[str, int]] = None

        if viewport is not None:
            viewport_element = {
                "width": viewport.width,
                "height": viewport.height,
            }

        browser_config: Dict[str, Any] = {
            "user_agent": self.browser_profile.user_agent,
            "viewport": viewport_element,
            "device_scale_factor": self.browser_profile.device_scale_factor,
            "color_scheme": self.browser_profile.color_scheme,
            "accept_downloads": self.browser_profile.accept_downloads,
            "proxy": self.browser_profile.proxy,
            "client_certificates": self.browser_profile.client_certificates,
            "extra_http_headers": self.browser_profile.extra_http_headers,
            "http_credentials": self.browser_profile.http_credentials,
            "java_script_enabled": self.browser_profile.java_script_enabled,
            "geolocation": self.browser_profile.geolocation,
            "timeout": self.browser_profile.timeout,
            "headers": self.browser_profile.headers,
            "allowed_domains": self.browser_profile.allowed_domains,
        }

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

        for idx, (model_taken_action, brain) in enumerate(
            zip(
                self.agent_taken_actions,
                self.state.history.model_thoughts(),
            )
        ):

            if verbose:
                rich_print(f"Step {idx + 1}:")
                rich_print("Log:")
                rich_print(model_taken_action)

            actions[f"action_{idx}"] = {
                "model_taken_action": model_taken_action,
                "brain": brain.model_dump(),
            }

        with open(traversal_file, "w") as f:
            json.dump(
                {
                    "browser_config": browser_config,
                    "actions": actions,
                },
                f,
                indent=4,
                ensure_ascii=False,
            )

        print(f"Traversal saved with ID: {timestamp}_{traversal_id}")
