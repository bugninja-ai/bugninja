import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from lxml import etree
from lxml.cssselect import CSSSelector

from browser_use.agent.service import (  # type: ignore
    Agent,
    AgentHistory,
    AgentStepInfo,
    BrowserStateHistory,
    logger,
)
from browser_use.agent.views import ActionResult, AgentHistoryList, StepMetadata, DOMElementNode  # type: ignore
from browser_use.utils import SignalHandler  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from cuid2 import Cuid as CUID
from rich import print as rich_print
from browser_use.dom.history_tree_processor.service import DOMHistoryElement

from browser_use.browser.session import Page
from browser_use.browser.profile import ViewportSize
from pydantic import BaseModel, Field
import time
from langchain_core.messages import HumanMessage
from browser_use.agent.message_manager.utils import save_conversation
import inspect
import json
from src.selector_factory import SelectorFactory, SelectorSpecificity

AgentHookFunc = Callable[["Agent"], Awaitable[None]]


class ExtraInteractionInfo(BaseModel):
    relative_xpath_selector: Optional[str] = Field(
        default=None, description="Relative XPath selector"
    )
    alternative_xpath_selectors: List[str] = Field(
        default_factory=list, description="Alternative XPath selectors"
    )
    alternative_css_selectors: List[str] = Field(
        default_factory=list, description="Alternative CSS selectors"
    )


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
        result: list[ActionResult] = []
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
            for action in model_output.action:
                short_action_descriptor: Dict[str, Any] = action.model_dump(exclude_none=True)
                action_key: str = list(short_action_descriptor.keys())[-1]

                #!! these values here were selected by hand, if necessary they can be extended with other actions as well
                if action_key in [
                    "click_element_by_index",
                    "input_text",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "drag_drop",
                ]:
                    action_index = short_action_descriptor[action_key]["index"]
                    chosen_selector: DOMElementNode = browser_state_summary.selector_map[
                        action_index
                    ]
                    logger.info(f"📄 {action_key} on {chosen_selector}")

                    selector_data: Dict[str, Any] = chosen_selector.__json__()

                    raw_html: str = await self.get_raw_html_of_current_page()

                    try:
                        factory = SelectorFactory(raw_html)

                        selector_data["alternative_relative_xpaths"] = (
                            factory.generate_relative_xpath_from_full_xpath(
                                full_xpath=selector_data.get("xpath")
                            )
                        )

                        rich_print(selector_data)
                    except Exception as e:
                        logger.error(f"Error generating alternative selectors: {e}")
                        selector_data["alternative_relative_xpaths"] = None

            result: list[ActionResult] = await self.multi_act(model_output.action)
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

    # @time_execution_async("--run (agent)")
    # async def run(
    #     self,
    #     max_steps: int = 100,
    #     on_step_start: AgentHookFunc | None = None,
    #     on_step_end: AgentHookFunc | None = None,
    # ) -> Optional[AgentHistoryList]:
    #     """Execute the task with maximum number of steps"""

    #     loop = asyncio.get_event_loop()
    #     agent_run_error: str | None = None  # Initialize error tracking variable
    #     self._force_exit_telemetry_logged = False  # ADDED: Flag for custom telemetry on force exit

    #     # Initialize the extra_info_for_steps list, that will hold additional information
    #     # relating to every interaction of the model
    #     #! IMPORTANT: these elements are not representing steps only, but e ery interaction of the model
    #     self.extra_info_for_steps: List[Dict[str, Any]] = []

    #     # this in interaction counter is here in order to measure the number of interactions of the model has taken
    #     # it is important so that we can keep track at each step that how many interactions did the model take at each step
    #     self.last_interaction_idx: int = 0

    #     # Define the custom exit callback function for second CTRL+C
    #     def on_force_exit_log_telemetry() -> None:
    #         self._log_agent_event(max_steps=max_steps, agent_run_error="SIGINT: Cancelled by user")
    #         # NEW: Call the flush method on the telemetry instance
    #         if hasattr(self, "telemetry") and self.telemetry:
    #             self.telemetry.flush()
    #         self._force_exit_telemetry_logged = True  # Set the flag

    #     signal_handler = SignalHandler(
    #         loop=loop,
    #         pause_callback=self.pause,
    #         resume_callback=self.resume,
    #         custom_exit_callback=on_force_exit_log_telemetry,  # Pass the new telemetrycallback
    #         exit_on_second_int=True,
    #     )
    #     signal_handler.register()

    #     try:
    #         self._log_agent_run()

    #         # Execute initial actions if provided
    #         if self.initial_actions:
    #             result = await self.multi_act(self.initial_actions, check_for_new_elements=False)
    #             self.state.last_result = result

    #         for step in range(max_steps):
    #             # Replace the polling with clean pause-wait
    #             if self.state.paused:
    #                 await self.wait_until_resumed()
    #                 signal_handler.reset()

    #             # Check if we should stop due to too many failures
    #             if self.state.consecutive_failures >= self.settings.max_failures:
    #                 logger.error(
    #                     f"❌ Stopping due to {self.settings.max_failures} consecutive failures"
    #                 )
    #                 agent_run_error = (
    #                     f"Stopped due to {self.settings.max_failures} consecutive failures"
    #                 )
    #                 break

    #             # Check control flags before each step
    #             if self.state.stopped:
    #                 logger.info("🛑 Agent stopped")
    #                 agent_run_error = "Agent stopped programmatically"
    #                 break

    #             while self.state.paused:
    #                 await asyncio.sleep(0.2)  # Small delay to prevent CPU spinning
    #                 if self.state.stopped:  # Allow stopping while paused
    #                     agent_run_error = "Agent stopped programmatically while paused"
    #                     break

    #             if on_step_start is not None:
    #                 await on_step_start(self)

    #             step_info = AgentStepInfo(step_number=step, max_steps=max_steps)
    #             await self.step(step_info)

    #             #! Important detail: a single step can have multiple actions!
    #             #! for this reason we have to keep track of the last interaction index
    #             taken_action_in_step: Dict[str, Any]

    #             for taken_action_in_step in self.state.history.model_actions()[
    #                 self.last_interaction_idx :
    #             ]:
    #                 interacted_element: Optional[DOMHistoryElement] = taken_action_in_step.get(
    #                     "interacted_element"
    #                 )

    #                 # we add a filler for the extra info, so that it will have the same length
    #                 self.extra_info_for_steps.append(ExtraInteractionInfo().model_dump())

    #                 # if there is element interaction in this step we try to improve the selector
    #                 if interacted_element:

    #                     rich_print(interacted_element)

    #                     current_page: Page = await self.browser_session.get_current_page()
    #                     await current_page.wait_for_load_state("domcontentloaded")
    #                     await current_page.wait_for_load_state("load")
    #                     html_content_of_page: str = await current_page.content()

    #                     self.extra_info_for_steps[-1] = ExtraInteractionInfo(
    #                         # relative_xpath_selector=generate_relative_xpath(
    #                         #     html_content=html_content_of_page,
    #                         #     full_xpath=interacted_element.xpath,
    #                         # ),
    #                         alternative_xpath_selectors=improve_xpath_selector(
    #                             html_text=html_content_of_page, dom_element=interacted_element
    #                         ),
    #                         alternative_css_selectors=improve_css_selector(
    #                             html_text=html_content_of_page, dom_element=interacted_element
    #                         ),
    #                     ).model_dump()

    #             self.last_interaction_idx = len(self.state.history.model_actions())

    #             if on_step_end is not None:
    #                 await on_step_end(self)

    #             if self.state.history.is_done():
    #                 if self.settings.validate_output and step < max_steps - 1:
    #                     if not await self._validate_output():
    #                         continue

    #                 await self.log_completion()

    #                 break
    #         else:
    #             agent_run_error = "Failed to complete task in maximum steps"

    #             self.state.history.history.append(
    #                 AgentHistory(
    #                     model_output=None,
    #                     result=[ActionResult(error=agent_run_error, include_in_memory=True)],
    #                     state=BrowserStateHistory(
    #                         url="",
    #                         title="",
    #                         tabs=[],
    #                         interacted_element=[],
    #                         screenshot=None,
    #                     ),
    #                     metadata=None,
    #                 )
    #             )

    #             logger.info(f"❌ {agent_run_error}")

    #         return self.state.history

    #     except KeyboardInterrupt:
    #         # Already handled by our signal handler, but catch any direct KeyboardInterrupt as well
    #         logger.info("Got KeyboardInterrupt during execution, returning current history")
    #         agent_run_error = "KeyboardInterrupt"
    #         return self.state.history

    #     except Exception as e:
    #         logger.error(f"Agent run failed with exception: {e}", exc_info=True)
    #         agent_run_error = str(e)
    #         raise e

    #     finally:
    #         # Unregister signal handlers before cleanup
    #         signal_handler.unregister()

    #         if not self._force_exit_telemetry_logged:  # MODIFIED: Check the flag
    #             try:
    #                 self._log_agent_event(max_steps=max_steps, agent_run_error=agent_run_error)
    #             except Exception as log_e:  # Catch potential errors during logging itself
    #                 logger.error(f"Failed to log telemetry event: {log_e}", exc_info=True)
    #         else:
    #             # ADDED: Info message when custom telemetry for SIGINT was already logged
    #             logger.info("Telemetry for force exit (SIGINT) was logged by custom exit callback.")

    #         await self.close()

    def save_q_agent_actions(self, verbose: bool = False) -> None:
        interactions: Dict[str, Any] = {}

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

        for idx, (model_taken_action, brain, action_details, extra_info) in enumerate(
            zip(
                self.state.history.model_actions(),
                self.state.history.model_thoughts(),
                self.state.history.model_outputs(),
            )
        ):
            brain_dict = brain.model_dump()
            action_details_dict = action_details.model_dump()
            model_taken_action: Dict[str, Any] = model_taken_action.copy()

            interacted_element: Optional[DOMHistoryElement] = model_taken_action.get(
                "interacted_element", None
            )

            if interacted_element is not None:

                #! Ensure the XPath starts with "//"
                if not interacted_element.xpath.startswith("//"):
                    interacted_element.xpath = f"//{interacted_element.xpath}"

                model_taken_action["interacted_element"] = (
                    interacted_element.to_dict() | extra_info.copy()
                )

            if verbose:
                rich_print(f"Step {idx + 1}:")
                rich_print("Model Action:")
                rich_print(model_taken_action)
                rich_print("Brain:")
                rich_print(brain)
                rich_print("Action Details:")
                rich_print(action_details)

            interactions[f"interaction_{idx}"] = {
                "model_taken_action": model_taken_action,
                "brain": brain_dict,
                "action_details": action_details_dict,
            }

        with open(traversal_file, "w") as f:
            json.dump(
                {
                    "browser_config": browser_config,
                    "interactions": interactions,
                },
                f,
                indent=4,
                ensure_ascii=False,
            )

        print(f"Traversal saved with ID: {timestamp}_{traversal_id}")
