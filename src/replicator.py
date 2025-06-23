"""
Browser Interaction Replicator

This module implements a class that can read and execute browser interactions
from a JSON log file. It processes each interaction sequentially and performs the
corresponding browser actions using Patchright (undetected Playwright).

The JSON log file contains steps with:
- model_taken_action: The action to perform
- interacted_element: Details about the element to interact with
- brain: Agent's reasoning and state
- action_details: Specific details about the action
"""

import asyncio
import gc
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from browser_use import BrowserProfile, BrowserSession  # type: ignore
from browser_use.agent.views import AgentBrain  # type: ignore
from patchright.async_api import BrowserContext as PatchrightBrowserContext
from patchright.async_api import Page
from rich import print as rich_print

from src.agents.healer_agent import HealerAgent
from src.models.model_configs import azure_openai_model
from src.schemas import BugninjaExtendedAction, StateComparison, Traversal

# Configure logging with custom format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _get_user_input() -> str:
    """
    Robust input method that forces stdin to work.
    """
    logger.info("⏸️ Press Enter to continue, or enter 'q' to quit...")

    # Try to reopen stdin if it's not working
    try:
        if not sys.stdin.isatty():
            # Force reopen stdin
            sys.stdin = open("/dev/tty", "r")
    except Exception:
        logger.warning("⚠️ Failed to reopen stdin - continuing automatically")

    try:
        return input()
    except EOFError:
        # Try alternative approach
        try:
            import select
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        ch = sys.stdin.read(1)
                        if ch == "\n" or ch == "\r":
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ""
        except Exception:
            logger.warning("⚠️ No input available - continuing automatically")
            return ""
    except Exception as e:
        logger.warning(f"⚠️ Input error: {e} - continuing automatically")
        return ""


class ReplicatorError(Exception):
    """Base exception for Replicator errors."""

    pass


class UserInterruptionError(ReplicatorError):
    """Exception raised when user interrupts the replication process."""

    pass


class SelectorError(ReplicatorError):
    """Exception raised when selector operations fail."""

    pass


class ActionError(ReplicatorError):
    """Exception raised when browser actions fail."""

    pass


class Replicator:
    """
    A class that replicates browser interactions from a JSON log file.

    This class reads a JSON file containing browser interaction steps and
    executes them sequentially using Patchright. Each interaction is processed
    and the corresponding browser action is performed with fallback mechanisms
    for element selection.
    """

    def __init__(
        self,
        json_path: str,
        fail_on_unimplemented_action: bool = False,
        sleep_after_actions: float = 1.0,
        pause_after_each_step: bool = True,
    ):
        """
        Initialize the Replicator with a JSON file path.

        Args:
            json_path: Path to the JSON file containing interaction steps
            fail_on_unimplemented_action: Whether to fail on unimplemented actions
            sleep_after_actions: Time to sleep after each action
            pause_after_each_step: Whether to pause and wait for Enter key after each step
            secrets: Dictionary of secrets to replace in actions
        """
        self.json_path = Path(json_path)
        self.replay_traversal = self._load_traversal_from_json()
        self.current_interaction = 0
        self.max_retries = 2
        self.retry_delay = 0.5
        self.sleep_after_actions = sleep_after_actions
        self.pause_after_each_step = pause_after_each_step
        self.failed = False
        self.failed_reason: Optional[Exception] = None
        self.secrets = self.replay_traversal.secrets
        self.brain_states: Dict[str, AgentBrain] = self.replay_traversal.brain_states
        self.fail_on_unimplemented_action = fail_on_unimplemented_action

        # Get the number of actions from the actions dictionary
        self.total_actions = len(self.replay_traversal.actions)
        logger.info(f"🚀 Initialized Replicator with {self.total_actions} steps to process")
        if self.pause_after_each_step:
            logger.info(
                "⏸️ Pause after each step is ENABLED - press Enter to continue after each action"
            )

    def _load_traversal_from_json(self) -> Traversal:
        """
        Load and parse the JSON file containing interaction steps.

        Returns:
            Dict containing the parsed JSON data
        """
        try:
            with open(self.json_path, "r") as f:
                data: Dict[str, Any] = json.load(f)  # type:ignore
                if "actions" not in data:
                    raise ReplicatorError("JSON file must contain an 'actions' key")
                logger.info(f"📄 Successfully loaded JSON file: {self.json_path}")
                return Traversal.model_validate(data)
        except Exception as e:
            logger.error(f"❌ Failed to load JSON file: {str(e)}")
            raise ReplicatorError(f"Failed to load JSON file: {str(e)}")

    def _wait_for_enter_key(self) -> None:
        """
        Wait for the user to press the Enter key to continue.

        This method provides a pause mechanism that allows users to review
        each step before proceeding to the next one.
        """
        try:
            user_input: str = _get_user_input()
            if user_input == "q":
                raise UserInterruptionError("User interrupted the replication process")
            logger.info("▶️ Continuing to next step...")
        except UserInterruptionError:
            logger.warning("⚠️ Interrupted by user ('q' pressed)")
            raise UserInterruptionError("User interrupted the replication process")
        except Exception as e:
            logger.error(f"❌ Unexpected error waiting for user input: {str(e)}")
            # Continue anyway to avoid blocking the process
            logger.info("▶️ Continuing to next step...")

    async def _try_selector(
        self, page: Page, selector: str, action: str, **kwargs: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Try to execute an action with a specific selector.

        Args:
            page: The page to execute the action on
            selector: The selector to use
            action: The action to perform ('click', 'fill', etc.)
            **kwargs: Additional arguments for the action

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        # Wait for page to be fully loaded
        await page.wait_for_load_state("load")
        await page.wait_for_load_state("domcontentloaded")

        logger.info(f"📝 Using selector: {selector}")

        try:
            # Get element and verify its state
            element = page.locator(selector)

            await element.wait_for(state="attached", timeout=1000)

            element_count = await element.count()
            logger.info(f"Found '{element_count}' elements for selector")

            if element_count == 0:
                logger.warning(f"⚠️ No elements found for selector: {selector}")
                return False, f"No elements found for selector: {selector}"
            if element_count > 1:
                logger.warning(f"⚠️ Multiple elements found for selector: {selector}")
                return False, f"Multiple elements found for selector: {selector}"

            if action == "click":
                await element.click()
            elif action == "fill":
                value: Optional[str] = kwargs.get("text")  # type:ignore

                if value is None:
                    logger.warning(f"⚠️ No value provided for {action} action")
                    return False, "No value provided for fill action"

                for key, secret_value in self.secrets.items():
                    secret_key = f"<secret>{key}</secret>"
                    if secret_key in value:
                        value = value.replace(f"<secret>{key}</secret>", secret_value)

                await element.fill(value)
            return True, None
        except Exception as e:
            error_msg = f"Failed to {action} with selector {selector}: {str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            return False, error_msg

    async def _get_element_selector(self, element_info: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Get a list of selectors for an element based on available information.
        Returns selectors in priority order: Primary XPath, then alternative relative XPaths.

        Args:
            element_info: Dictionary containing element information

        Returns:
            List of tuples containing (selector_type, selector_value)

        Raises:
            SelectorError: If no valid selectors can be generated
        """
        selectors = []

        # Add primary XPath if available
        if element_info.get("xpath"):
            selectors.append(("xpath", element_info["xpath"]))
            logger.debug(f"🎯 Added primary XPath selector: {element_info['xpath']}")

        # Add alternative relative XPaths if available
        if element_info.get("alternative_relative_xpaths"):
            for xpath in element_info["alternative_relative_xpaths"]:
                selectors.append(("xpath", xpath))
                logger.debug(f"🎯 Added alternative XPath selector: {xpath}")

        # If no selectors were found, try to construct a basic selector
        if not selectors:
            tag = element_info.get("tag_name", "")
            attrs = element_info.get("attributes", {})

            if not tag:
                raise SelectorError("No valid selector information available")

            # Construct a valid CSS selector
            if attrs:
                attr_pairs = [f"{k}='{v}'" for k, v in attrs.items()]
                selector = f"{tag}[{', '.join(attr_pairs)}]"
            else:
                selector = tag

            selectors.append(("css", selector))
            logger.debug(f"🎯 Using fallback selector: {selector}")

        return selectors

    async def _execute_with_fallback(
        self,
        action_type: str,
        element_info: Dict[str, Any],
        action_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute an action with selector fallback mechanism.

        Args:
            action_type: Type of action to perform ('click' or 'fill')
            element_info: Information about the element to interact with
            action_kwargs: Additional arguments for the action

        Raises:
            ActionError: If the action fails after trying all selectors
        """
        if not element_info:
            raise ActionError("No element information provided")

        selectors = await self._get_element_selector(element_info)
        logger.info(f"🖱️ Attempting to {action_type} element with {len(selectors)} selectors")

        last_error = None
        for selector_type, selector in selectors:
            logger.info(f"🔄 Trying {selector_type} selector: {selector}")
            success, error = await self._try_selector(
                self.current_page, selector, action_type, **(action_kwargs or {})
            )

            if success:
                logger.info(
                    f"✅ Successfully {action_type}ed element using {selector_type} selector"
                )
                return

            last_error = error
            logger.warning(f"⚠️ Selector failed: {error}")

        # If we get here, all selectors failed
        failed_selectors = [f"{type}: {sel}" for type, sel in selectors]
        error_msg = (
            f"Failed to {action_type} element. "
            f"Tried selectors: {', '.join(failed_selectors)}. "
            f"Last error: {last_error}"
        )
        raise ActionError(error_msg)

    async def _handle_go_to_url(self, action: Dict[str, Any]) -> None:
        """Handle navigation to a URL."""
        url = action["go_to_url"]["url"]
        logger.info(f"🌐 Navigating to URL: {url}")

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                await self.current_page.goto(url, wait_until="load")
                return
            except Exception as e:
                if "net::ERR_NETWORK_CHANGED" in str(e) and attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ Network error occurred, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

    async def _handle_click(self, element_info: Optional[Dict[str, Any]]) -> None:
        """Handle clicking an element."""

        if not element_info:
            raise ActionError("No element information provided for event 'click'!")

        await self._execute_with_fallback("click", element_info)

    async def _handle_input_text(
        self, action: Dict[str, Any], element_info: Optional[Dict[str, Any]]
    ) -> None:
        """Handle text input."""

        if not element_info:
            raise ActionError("No element information provided for event 'fill'!")

        await self._execute_with_fallback(
            "fill", element_info, {"text": action["input_text"]["text"]}
        )

    async def __handle_not_implemented_action(self, feature_name: str) -> None:
        if self.fail_on_unimplemented_action:
            raise ActionError(f"{feature_name} not yet implemented")

    async def _handle_extract_content(self) -> None:
        """Handle content extraction."""
        logger.info("📋 Content extraction requested")
        await self.__handle_not_implemented_action("Content extraction")

    async def _handle_wait(self) -> None:
        """Handle waiting."""
        logger.info("⏳ Waiting requested")
        await self.__handle_not_implemented_action("Waiting functionality")

    async def _handle_go_back(self) -> None:
        """Handle navigation back."""
        logger.info("⬅️ Go back requested")
        await self.__handle_not_implemented_action("Back navigation")

    async def _handle_search_google(self) -> None:
        """Handle Google search."""
        logger.info("🔍 Google search requested")
        await self.__handle_not_implemented_action("Google search")

    async def _handle_save_pdf(self) -> None:
        """Handle PDF saving."""
        logger.info("📄 PDF save requested")
        await self.__handle_not_implemented_action("PDF saving")

    async def _handle_switch_tab(self, switch_tab_id: Optional[int]) -> None:
        """Handle tab switching."""
        logger.info("🔄 Tab switch requested")

        #! precautionary sleep, so that the tab has time to load
        await asyncio.sleep(1)

        if switch_tab_id is None:
            raise ActionError("No page ID provided for tab switching")

        contexts: List[PatchrightBrowserContext] = self.browser_session.browser.contexts

        if not len(contexts):
            raise ActionError("No browser contexts found for tab switching")

        current_context: PatchrightBrowserContext = contexts[0]

        if not len(current_context.pages):
            raise ActionError("No pages found for tab switching")

        self.current_page: Page = current_context.pages[switch_tab_id]

        await self.current_page.bring_to_front()

    async def _handle_open_tab(self) -> None:
        """Handle opening new tab."""
        logger.info("➕ New tab requested")
        await self.__handle_not_implemented_action("New tab")

    async def _handle_close_tab(self) -> None:
        """Handle closing tab."""
        logger.info("❌ Tab close requested")
        await self.__handle_not_implemented_action("Tab closing")

    async def _handle_get_ax_tree(self) -> None:
        """Handle getting accessibility tree."""
        logger.info("🌳 Accessibility tree requested")
        await self.__handle_not_implemented_action("Accessability tree request")

    async def _scroll(self, scroll_amount: Optional[int], how: Literal["up", "down"]) -> None:
        """Handle scrolling to a specific direction."""
        logger.info(f"⬇️ Scroll {how} requested")
        """
			(a) Use browser._scroll_container for container-aware scrolling.
			(b) If that JavaScript throws, fall back to window.scrollBy().
		"""

        dy = scroll_amount or await self.current_page.evaluate("() => window.innerHeight")

        if how == "up":
            dy = -dy

        await self.current_page.wait_for_timeout(500)

        await self.current_page.evaluate("(y) => window.scrollBy(0, y)", dy)
        logger.info(f"🔍 Scrolled down the page by {dy} pixels")

    async def _handle_scroll_down(self, scroll_amount: Optional[int]) -> None:
        """Handle scrolling down."""
        await self._scroll(scroll_amount, "down")

    async def _handle_scroll_up(self, scroll_amount: Optional[int]) -> None:
        """Handle scrolling up."""
        await self._scroll(scroll_amount, "up")

    async def _handle_send_keys(self) -> None:
        """Handle sending keys."""
        logger.info("⌨️ Send keys requested")
        await self.__handle_not_implemented_action("Send keys")

    async def _handle_scroll_to_text(self) -> None:
        """Handle scrolling to text."""
        logger.info("🔍 Scroll to text requested")
        await self.__handle_not_implemented_action("Scroll to text")

    async def _handle_get_dropdown_options(self) -> None:
        """Handle getting dropdown options."""
        logger.info("📝 Dropdown options requested")
        await self.__handle_not_implemented_action("Dropdown options")

    async def _handle_select_dropdown_option(self) -> None:
        """Handle selecting dropdown option."""
        logger.info("✅ Dropdown selection requested")
        await self.__handle_not_implemented_action("Dropdown selection")

    async def _handle_drag_drop(self) -> None:
        """Handle drag and drop."""
        logger.info("🔄 Drag and drop requested")
        await self.__handle_not_implemented_action("Drag and drop")

    async def _handle_done(self) -> None:
        """Handle done action."""
        logger.info("✅ Done action received")
        # This is a status indicator, not an error
        return

    #! The 'can_be_skipped flag has been added for a specific reason.
    #! If there are steps taken by the original AI agent that do not necessarily contribute for the completion of the whole flow, the specific element can be skipped.
    #! Right now, we do not have a solution to automatically map which steps of specific flows can be or should be skipped, but in the upcoming features,
    #! I will most likely develop an AI agent solution for this.

    async def _execute_action(
        self, interaction: BugninjaExtendedAction, can_be_skipped: bool = False
    ) -> None:
        """
        Execute a single interaction's action using Patchright with retry mechanism.

        Args:
            interaction: Dictionary containing the interaction information
            can_be_skipped: Whether this interaction can be skipped

        Raises:
            ActionError: If the action fails after all retries
        """
        if can_be_skipped:
            logger.info(f"📝 Skipping interaction: {interaction}")
            return

        # Log brain information before executing the action
        brain: Optional[AgentBrain] = self.brain_states.get(interaction.brain_state_id)

        if not brain:
            error_msg = f"🚫 No brain information found for interaction: {interaction}"
            logger.error(error_msg)
            raise ActionError(error_msg)

        logger.info("\n")
        logger.info("🧠 Current State:")
        logger.info(f"📝 Memory: {brain.memory}")
        logger.info(f"🎯 Next Goal: {brain.next_goal}")
        logger.info(f"✅ Previous Evaluation: {brain.evaluation}")
        logger.info("=" * 20)

        # TODO! Do here a major refactor with a lot of custom schemas,
        #! otherwise dictionary drilling will be pain and also makes the code hard to debug

        element_info: Optional[Dict[str, Any]] = interaction.dom_element_data

        switch_tab_action: Optional[Dict[str, Any]] = interaction.action.get("switch_tab")
        scroll_down_action: Optional[Dict[str, Any]] = interaction.action.get("scroll_down")
        scroll_up_action: Optional[Dict[str, Any]] = interaction.action.get("scroll_down")

        scroll_amount: Optional[int] = None
        switch_tab_id: Optional[int] = None

        if switch_tab_action:
            switch_tab_id = switch_tab_action["tab_id"]

        if scroll_down_action:
            scroll_amount = scroll_down_action["amount"]

        if scroll_up_action:
            scroll_amount = scroll_up_action["amount"]

        # Map actions to their handlers
        action_handlers = {
            "go_to_url": lambda: self._handle_go_to_url(action=interaction.action),
            "click_element_by_index": lambda: self._handle_click(element_info=element_info),
            "input_text": lambda: self._handle_input_text(
                action=interaction.action, element_info=element_info
            ),
            "extract_content": self._handle_extract_content,
            "wait": self._handle_wait,
            "go_back": self._handle_go_back,
            "search_google": self._handle_search_google,
            "save_pdf": self._handle_save_pdf,
            "switch_tab": lambda: self._handle_switch_tab(switch_tab_id=switch_tab_id),
            "open_tab": self._handle_open_tab,
            "close_tab": self._handle_close_tab,
            "get_ax_tree": self._handle_get_ax_tree,
            "scroll_down": lambda: self._handle_scroll_down(scroll_amount=scroll_amount),
            "scroll_up": lambda: self._handle_scroll_up(scroll_amount=scroll_amount),
            "send_keys": self._handle_send_keys,
            "scroll_to_text": self._handle_scroll_to_text,
            "get_dropdown_options": self._handle_get_dropdown_options,
            "select_dropdown_option": self._handle_select_dropdown_option,
            "drag_drop": self._handle_drag_drop,
            "done": self._handle_done,
        }

        # Get the appropriate handler for the action
        non_none_action: Dict[str, Any] = {
            k: v for k, v in interaction.action.items() if v is not None
        }

        handler = action_handlers.get(list(non_none_action.keys())[0])

        if handler:
            await handler()
            #! precautionary sleep so that the replay function has time to catch up
            await asyncio.sleep(self.sleep_after_actions)
        else:
            raise ActionError(f"Unknown action type: {interaction.action}")

    async def evaluate_current_state(
        # TODO! later add here proper typing in oder to get rid of type matching problems
        self,
        current_state: Dict[str, Any],
        upcoming_states: List[Dict[str, Any]],
    ) -> StateComparison:
        # Read the system prompt
        system_prompt_path = Path(__file__).parent / "prompts" / "state_comp_system_prompt.md"
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()

        # Read the user prompt template
        user_prompt_path = Path(__file__).parent / "prompts" / "state_comp_user_prompt.md"
        with open(user_prompt_path, "r") as f:
            user_prompt_template = f.read()

        # Replace placeholders with actual data
        user_prompt = user_prompt_template.replace(
            "[[CURRENT_STATE_JSON]]", json.dumps(current_state, indent=4, ensure_ascii=False)
        ).replace(
            "[[UPCOMING_STATES]]",
            json.dumps(
                {"upcoming_states": [{"idx": idx} | s for idx, s in enumerate(upcoming_states)]},
                indent=4,
                ensure_ascii=False,
            ),
        )

        json_llm = azure_openai_model().bind(response_format={"type": "json_object"})
        ai_msg = json_llm.invoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        response_json: Dict[str, Any] = ai_msg.content  # type: ignore

        return StateComparison.model_validate(response_json)

    # def create_agent_state_from_traversal_json(self, cut_after: Optional[int] = None) -> AgentState:
    #     """
    #     Convert brain states from the loaded traversal JSON to AgentState structure.

    #     This method takes the brain_states from the replay JSON and converts them
    #     into the proper AgentState structure that can be used by the healer agent.

    #     Returns:
    #         AgentState: Complete agent state with history from the traversal JSON
    #     """
    #     agent_history_list = []

    #     # Process each brain state in chronological order
    #     for action_key in sorted(self.replay_traversal["actions"].keys()):
    #         action_data = self.replay_traversal["actions"][action_key]
    #         brain_state_id = action_data["model_taken_action"].get("brain_state_id")

    #         if brain_state_id and brain_state_id in self.brain_states:
    #             brain_state = self.brain_states[brain_state_id]

    #             # Create AgentBrain from the brain state
    #             agent_brain = AgentBrain(
    #                 evaluation_previous_goal=brain_state.get("evaluation_previous_goal", ""),
    #                 memory=brain_state.get("memory", ""),
    #                 next_goal=brain_state.get("next_goal", ""),
    #             )

    #             # Create AgentOutput with the brain state and empty action
    #             agent_output = AgentOutput(
    #                 current_state=agent_brain,
    #                 action=[],  # Empty action list since this is historical data
    #             )

    #             # Create minimal BrowserStateHistory
    #             # Note: We don't have detailed browser state info in the JSON
    #             browser_state = BrowserStateHistory(
    #                 url="",  # Could be extracted from action if needed
    #                 title="",
    #                 interacted_element=[],
    #                 tabs=[],
    #             )

    #             # Create AgentHistory entry
    #             agent_history = AgentHistory(
    #                 model_output=agent_output,
    #                 result=[],  # Empty result since this is historical data
    #                 state=browser_state,
    #             )

    #             agent_history_list.append(agent_history)

    #     # Create AgentHistoryList
    #     history_list = AgentHistoryList(history=agent_history_list)

    #     if cut_after:
    #         history_list.history = history_list.history[:cut_after]

    #     # Create and return AgentState
    #     return AgentState(history=history_list)

    def create_self_healing_agent(self, at_idx: int) -> HealerAgent:
        """
        Start the self-healing agent.
        """

        agent = HealerAgent(
            task=self.replay_traversal.test_case,
            llm=azure_openai_model(),
            browser_session=self.browser_session,
            sensitive_data=self.secrets,
            # TODO! experiment with adding the proper state from previous runs for the brain to be aware what is happening
            # injected_agent_state=self.create_agent_state_from_traversal_json(cut_after=at_idx),
        )

        return agent

    async def self_healing_action(self, at_idx: int) -> None:

        #!!!! TODO! First try goes with BARE self healing agent
        #!!!! - No previous thought process provided
        #!!!! - No previous history provided yet

        upcoming_state_ids: List[str] = [
            brain_state_id
            for brain_state_id in self.brain_states.keys()
            if brain_state_id not in self.brain_states_passed
        ]

        upcoming_states: List[Dict[str, Any]] = [
            self.brain_states.get(brain_state_id) for brain_state_id in upcoming_state_ids
        ]

        healer_agent: HealerAgent = self.create_self_healing_agent(at_idx=at_idx)

        # TODO! healing agent should have its own complex implementation of running
        await healer_agent.step()

        if not len(healer_agent.agent_taken_actions):
            raise ActionError(
                "Self healing agent failed to find a solution for this specific state"
            )

        brain_state_id: Optional[str] = healer_agent.agent_taken_actions[-1].get("brain_state_id")

        if not brain_state_id:
            raise ActionError(
                "There is an error relating to pairing 'brain_state_id' to specific actions!"
            )

        healer_agent_state: Dict[str, Any] = healer_agent.agent_brain_states[brain_state_id]

        rich_print(
            [self.brain_states.get(brain_state_id) for brain_state_id in self.brain_states_passed]
        )
        rich_print(healer_agent_state)
        rich_print(upcoming_states)

        model_response: StateComparison = await self.evaluate_current_state(
            current_state=healer_agent_state, upcoming_states=upcoming_states
        )

        rich_print(model_response)

    async def run(self, can_be_skipped_steps_list: List[int] = []) -> None:
        """
        Run through all steps in the JSON file and execute them.

        This method processes each interaction sequentially, executing the
        corresponding browser action for each interaction. If an action fails,
        it attempts self-healing before continuing or failing the replication.
        """
        # try:
        logger.info("🚀 Starting browser session")

        self.browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                # ? these None settings are necessary in order for every new run to be perfectly independent and clean
                user_data_dir=None,
                storage_state=None,
                # Apply browser configuration if available
                **self.replay_traversal.browser_config.model_dump(exclude_none=True),
            )
        )

        await self.browser_session.start()
        self.current_page = await self.browser_session.get_current_page()

        self.brain_states_passed: List[str] = []

        # Process actions in order
        for idx, (element_key, interaction) in enumerate(self.replay_traversal.actions.items()):
            action_key = f"action_{idx}"
            if element_key != action_key:
                error_msg: str = (
                    f"⚠️ There is a mismatch between element key and action key! '{element_key}' != '{action_key}'"
                )
                logger.error(error_msg)
                raise ActionError(error_msg)

            logger.info(f"📝 Executing interaction: {action_key}")

            try:
                # TODO! needs much more robust error handling for different kinds of errors
                interaction_can_be_skipped: bool = idx in can_be_skipped_steps_list

                await self._execute_action(interaction, can_be_skipped=interaction_can_be_skipped)

                brain_state_id = interaction.brain_state_id

                # ? mark current state as passed
                if brain_state_id not in self.brain_states_passed:
                    self.brain_states_passed.append(brain_state_id)

                # Add pause after action if enabled and action was not skipped
                if self.pause_after_each_step and idx not in can_be_skipped_steps_list:
                    self._wait_for_enter_key()

                self.current_interaction += 1

            except UserInterruptionError as e:
                logger.info("⏹️ User interrupted replication process")
                self.failed = True
                self.failed_reason = e
                break

            except Exception as e:
                logger.error(f"❌ Error in interaction {action_key}: {str(e)}")
                logger.info("🔄 Attempting self-healing...")
                logger.info("Marking current state as failed...")

                # ? this functionality here is crucial for handling the "failing states"
                # ? since a single state can have multiple action, an action can fail in the middle of a state
                # ? to prevent from excluding the state from comparison we need to keep track of the last passed state
                # ? here we flag the last state as not passed
                self.brain_states_passed.pop(-1)

                try:
                    # Attempt self-healing

                    await self.self_healing_action(at_idx=idx)

                    # Add pause after healing if enabled
                    if self.pause_after_each_step and idx not in can_be_skipped_steps_list:
                        self._wait_for_enter_key()

                    self.current_interaction += 1

                except UserInterruptionError as e:
                    logger.info("⏹️ User interrupted the healing process")
                    self.failed = True
                    self.failed_reason = e
                    break

                except Exception as healing_error:
                    logger.error(f"❌ Self-healing failed: {str(healing_error)}")
                    logger.error(
                        "❌ Both original action and self-healing failed - stopping replication"
                    )
                    self.failed = True
                    self.failed_reason = Exception(
                        f"Action failed: {str(e)}. Self-healing failed: {str(healing_error)}"
                    )
                    break

        logger.info("🧹 Cleaning up resources")
        await self.cleanup()

        if self.failed:
            logger.error("❌ Replication failed")
            raise Exception(self.failed_reason)
        else:
            logger.info("✅ Replication completed successfully")

    async def cleanup(self) -> None:
        """
        Clean up resources after execution.

        This method closes the browser and playwright instance.
        """

        if self.current_page:
            await self.current_page.close()
            logger.debug("✅ Page closed")
        if self.browser_session.browser:
            await self.browser_session.browser.close()
            logger.debug("✅ Browser closed")
        if self.browser_session.playwright:
            await self.browser_session.playwright.stop()
            logger.debug("✅ Playwright stopped")

        await self.browser_session.close()

        gc.collect()

        logger.info("✨ Cleanup completed")
