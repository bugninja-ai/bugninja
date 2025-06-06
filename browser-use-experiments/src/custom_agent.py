import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from browser_use.agent.service import (  # type: ignore
    Agent,
    AgentHistory,
    AgentStepInfo,
    BrowserStateHistory,
    logger,
)
from browser_use.agent.views import ActionResult, AgentHistoryList  # type: ignore
from browser_use.utils import SignalHandler  # type: ignore
from browser_use.utils import time_execution_async  # type: ignore
from cuid2 import Cuid as CUID
from rich import print as rich_print
from browser_use.dom.history_tree_processor.service import DOMHistoryElement

AgentHookFunc = Callable[["Agent"], Awaitable[None]]


class QuinoAgent(Agent):
    @time_execution_async("--run (agent)")
    async def run(
        self,
        max_steps: int = 100,
        on_step_start: AgentHookFunc | None = None,
        on_step_end: AgentHookFunc | None = None,
    ) -> Optional[AgentHistoryList]:
        """Execute the task with maximum number of steps"""

        loop = asyncio.get_event_loop()
        agent_run_error: str | None = None  # Initialize error tracking variable
        self._force_exit_telemetry_logged = False  # ADDED: Flag for custom telemetry on force exit

        # Define the custom exit callback function for second CTRL+C
        def on_force_exit_log_telemetry() -> None:
            self._log_agent_event(max_steps=max_steps, agent_run_error="SIGINT: Cancelled by user")
            # NEW: Call the flush method on the telemetry instance
            if hasattr(self, "telemetry") and self.telemetry:
                self.telemetry.flush()
            self._force_exit_telemetry_logged = True  # Set the flag

        signal_handler = SignalHandler(
            loop=loop,
            pause_callback=self.pause,
            resume_callback=self.resume,
            custom_exit_callback=on_force_exit_log_telemetry,  # Pass the new telemetrycallback
            exit_on_second_int=True,
        )
        signal_handler.register()

        try:
            self._log_agent_run()

            # Execute initial actions if provided
            if self.initial_actions:
                result = await self.multi_act(self.initial_actions, check_for_new_elements=False)
                self.state.last_result = result

            for step in range(max_steps):
                # Replace the polling with clean pause-wait
                if self.state.paused:
                    await self.wait_until_resumed()
                    signal_handler.reset()

                # Check if we should stop due to too many failures
                if self.state.consecutive_failures >= self.settings.max_failures:
                    logger.error(
                        f"❌ Stopping due to {self.settings.max_failures} consecutive failures"
                    )
                    agent_run_error = (
                        f"Stopped due to {self.settings.max_failures} consecutive failures"
                    )
                    break

                # Check control flags before each step
                if self.state.stopped:
                    logger.info("🛑 Agent stopped")
                    agent_run_error = "Agent stopped programmatically"
                    break

                while self.state.paused:
                    await asyncio.sleep(0.2)  # Small delay to prevent CPU spinning
                    if self.state.stopped:  # Allow stopping while paused
                        agent_run_error = "Agent stopped programmatically while paused"
                        break

                if on_step_start is not None:
                    await on_step_start(self)

                step_info = AgentStepInfo(step_number=step, max_steps=max_steps)
                await self.step(step_info)

                if on_step_end is not None:
                    await on_step_end(self)

                if self.state.history.is_done():
                    if self.settings.validate_output and step < max_steps - 1:
                        if not await self._validate_output():
                            continue

                    await self.log_completion()
                    break
            else:
                agent_run_error = "Failed to complete task in maximum steps"

                self.state.history.history.append(
                    AgentHistory(
                        model_output=None,
                        result=[ActionResult(error=agent_run_error, include_in_memory=True)],
                        state=BrowserStateHistory(
                            url="",
                            title="",
                            tabs=[],
                            interacted_element=[],
                            screenshot=None,
                        ),
                        metadata=None,
                    )
                )

                logger.info(f"❌ {agent_run_error}")

            return self.state.history

        except KeyboardInterrupt:
            # Already handled by our signal handler, but catch any direct KeyboardInterrupt as well
            logger.info("Got KeyboardInterrupt during execution, returning current history")
            agent_run_error = "KeyboardInterrupt"
            return self.state.history

        except Exception as e:
            logger.error(f"Agent run failed with exception: {e}", exc_info=True)
            agent_run_error = str(e)
            raise e

        finally:
            # Unregister signal handlers before cleanup
            signal_handler.unregister()

            if not self._force_exit_telemetry_logged:  # MODIFIED: Check the flag
                try:
                    self._log_agent_event(max_steps=max_steps, agent_run_error=agent_run_error)
                except Exception as log_e:  # Catch potential errors during logging itself
                    logger.error(f"Failed to log telemetry event: {log_e}", exc_info=True)
            else:
                # ADDED: Info message when custom telemetry for SIGINT was already logged
                logger.info("Telemetry for force exit (SIGINT) was logged by custom exit callback.")

            await self.close()

    def save_q_agent_actions(self, verbose: bool = False) -> None:
        steps: Dict[str, Any] = {}

        traversal_dir = Path("./traversals")

        # Create traversals directory if it doesn't exist
        os.makedirs(traversal_dir, exist_ok=True)

        # Generate a unique ID for this traversal
        traversal_id = CUID().generate()

        # Get current timestamp in a readable format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save the traversal data with timestamp and unique ID
        traversal_file = traversal_dir / f"traverse_{timestamp}_{traversal_id}.json"

        for idx, (model_taken_action, brain, action_details) in enumerate(
            zip(
                self.state.history.model_actions(),
                self.state.history.model_thoughts(),
                self.state.history.model_outputs(),
            )
        ):
            brain_dict = brain.model_dump()
            action_details_dict = action_details.model_dump()
            model_taken_action = model_taken_action.copy()

            interacted_element: Optional[DOMHistoryElement] = model_taken_action.get(
                "interacted_element", None
            )

            if interacted_element is not None:
                model_taken_action["interacted_element"] = interacted_element.to_dict()

            if verbose:
                rich_print(f"Step {idx + 1}:")
                rich_print("Model Action:")
                rich_print(model_taken_action)
                rich_print("Brain:")
                rich_print(brain)
                rich_print("Action Details:")
                rich_print(action_details)

            steps[f"step_{idx}"] = {
                "model_taken_action": model_taken_action,
                "brain": brain_dict,
                "action_details": action_details_dict,
            }

        rich_print(steps)

        with open(traversal_file, "w") as f:
            json.dump(steps, f, indent=4, ensure_ascii=False)

        print(f"Traversal saved with ID: {timestamp}_{traversal_id}")
