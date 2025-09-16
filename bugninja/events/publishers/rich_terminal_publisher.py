"""
Rich terminal event publisher for Bugninja framework.

This module provides a rich terminal-based event publisher that displays
browser automation operations, run states, and action events with colored
output using the Rich library.
"""

import uuid
from typing import Any, Dict, Optional

from browser_use.agent.views import AgentBrain  # type: ignore
from rich.console import Console
from rich.text import Text

# Import the new high-level API
from bugninja.events.base import EventPublisher
from bugninja.events.exceptions import PublisherUnavailableError
from bugninja.events.models import RunState
from bugninja.schemas.pipeline import BugninjaExtendedAction


class RichTerminalPublisher(EventPublisher):
    """Rich terminal-based event publisher with colored output.

    This publisher provides real-time visual feedback for browser automation
    operations using the Rich library for enhanced terminal output. It displays
    run initialization, state updates, action events, and completion status
    with colored text and emojis for better user experience.

    Attributes:
        console (Console): Rich console instance for output
        _available (bool): Whether the publisher is available
        style (str): Color style for output messages

    Example:
        ```python
        from bugninja.events.publishers import RichTerminalPublisher

        # Create publisher
        publisher = RichTerminalPublisher()

        # Initialize a run
        run_id = await publisher.initialize_run("navigation", {"task": "test"})

        # Update run state
        await publisher.update_run_state(run_id, RunState(current_action="click"))

        # Complete the run
        await publisher.complete_run(run_id, success=True)
        ```
    """

    def __init__(self) -> None:
        """Initialize the rich terminal publisher.

        Sets up the Rich console and default styling for output messages.
        """
        self.console = Console()
        self._available = True
        self.style = "bright_blue"

    def is_available(self) -> bool:
        """Check if rich terminal publisher is available (always True)."""
        return self._available

    async def initialize_run(
        self, run_type: str, metadata: Dict[str, Any], existing_run_id: Optional[str] = None
    ) -> str:
        """Initialize a run with rich terminal output.

        Args:
            run_type (str): Type of run
            metadata (Dict[str, Any]): Run metadata
            existing_run_id (Optional[str]): Existing run ID for compatibility reasons, but not used in any way

        Returns:
            str: Generated run ID

        Raises:
            PublisherUnavailableError: If publisher is not available for any reason
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        run_id = f"rich_run_{uuid.uuid4().hex[:8]}"

        # Create blue colored message
        message = Text("🚀 Starting navigation run", style=self.style)
        self.console.print(message)

        # Print metadata if available
        if metadata.get("task_description"):
            task_msg = Text(
                f"📋 BugninjaTask: {metadata['task_description'][:100]}...", style=self.style
            )
            self.console.print(task_msg)

        return run_id

    async def update_run_state(self, run_id: str, state: RunState) -> None:
        """Update run state with rich terminal output.

        Args:
            run_id: ID of the run to update
            state: New state of the run

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        # Print progress updates in blue
        if state.current_action:
            action_msg = Text(f"⚙️ Action: {state.current_action}", style=self.style)
            self.console.print(action_msg)

    async def complete_run(self, run_id: str, success: bool, error: Optional[str] = None) -> None:
        """Complete run with rich terminal output.

        Args:
            run_id: ID of the run to complete
            success: Whether the run was successful
            error: Error message if run failed

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        if success:
            message = Text("🎉 Navigation completed successfully!", style=self.style)
        else:
            message = Text(f"❌ Navigation failed: {error}", style=self.style)

        self.console.print(message)

    async def publish_action_event(
        self,
        run_id: str,
        brain_state_id: str,
        actual_brain_state: AgentBrain,
        action_result_data: BugninjaExtendedAction,
    ) -> None:
        """Publish action event with rich terminal output.

        Args:
            run_id (str): ID of the run this action belongs to
            brain_state_id (str): ID of the brain state for this action
            actual_brain_state (AgentBrain): The actual brain state from the agent
            action_result_data (BugninjaExtendedAction): Extended action data with results

        Raises:
            PublisherUnavailableError: If publisher is not available

        Example:
            ```python
            # This method is typically called internally by the event system
            await publisher.publish_action_event(
                run_id="run_123",
                brain_state_id="state_456",
                actual_brain_state=brain_state,
                action_result_data=action_data
            )
            ```
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        action_type: str = action_result_data.get_action_type()

        action_done: Dict[str, Any] = action_result_data.action[action_type]

        # Print action event details in blue
        action_msg = Text(
            f"🔍 Action Event: '{action_type}' - {action_done}",
            style=self.style,
        )
        self.console.print(action_msg)
