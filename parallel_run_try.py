"""
Main execution script for Bugninja browser automation tasks.

This script demonstrates how to use the Bugninja high-level API for
browser automation tasks with proper configuration and error handling.
"""

import asyncio
import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from faker import Faker
from rich.console import Console
from rich.text import Text

# Import the new high-level API
from bugninja.api import BugninjaClient, Task
from bugninja.api.models import BugninjaConfig
from bugninja.config import ConfigurationFactory
from bugninja.events import EventPublisherManager
from bugninja.events.base import EventPublisher
from bugninja.events.exceptions import PublisherUnavailableError
from bugninja.events.models import RunEvent, RunState

# Initialize faker for generating test data
fake = Faker()

# Load environment variables
load_dotenv()

# Get settings for authentication prompt
settings = ConfigurationFactory.get_settings()


class RichTerminalPublisher(EventPublisher):
    """Rich terminal-based event publisher with colored output."""

    def __init__(self) -> None:
        """Initialize the rich terminal publisher."""
        self.console = Console()
        self._available = True
        self.style = "bright_blue"

    def is_available(self) -> bool:
        """Check if rich terminal publisher is available (always True)."""
        return self._available

    async def initialize_run(self, run_type: str, metadata: Dict[str, Any]) -> str:
        """Initialize a run with rich terminal output.

        Args:
            run_type: Type of run
            metadata: Run metadata

        Returns:
            Generated run ID

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        run_id = f"rich_run_{uuid.uuid4().hex[:8]}"

        # Create blue colored message
        message = Text("🚀 Starting navigation run", style=self.style)
        self.console.print(message)

        # Print metadata if available
        if metadata.get("task_description"):
            task_msg = Text(f"📋 Task: {metadata['task_description'][:100]}...", style=self.style)
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

    async def publish_event(self, event: RunEvent) -> None:
        """Publish event with rich terminal output.

        Args:
            event: Event to publish

        Raises:
            PublisherUnavailableError: If publisher is not available
        """
        if not self.is_available():
            raise PublisherUnavailableError("Rich terminal publisher is not available")

        # Handle different event types with appropriate messages
        if event.event_type == "step_completed":
            self.console.print(f"📋 Step completed event:\n{event}", style=self.style)

        elif event.event_type == "action_completed":
            self.console.print(f"✅ Action completed event:\n{event}", style=self.style)

        elif event.event_type == "healing_started":
            message = Text("🩹 Starting healing process...", style=self.style)
            self.console.print(message)

        elif event.event_type == "run_completed":
            success = event.data.get("success", True)
            healing_used = event.data.get("healing_used", False)
            if success:
                if healing_used:
                    message = Text("🎉 Navigation completed with healing!", style=self.style)
                else:
                    message = Text("🎉 Navigation completed successfully!", style=self.style)
            else:
                message = Text("❌ Navigation failed", style=self.style)
            self.console.print(message)

        elif event.event_type == "run_failed":
            error = event.data.get("error", "Unknown error")
            message = Text(f"❌ Navigation failed: {error}", style=self.style)
            self.console.print(message)


# Task definitions
BACPREP_NAVIGATION_PROMPT = """
Go to app.bacprep.ro/en, login to the platform via email authentication with the 
provided credentials and edit the name of the user based on the provided information. 
If successful log out and close the browser.
""".strip()


async def main() -> None:
    """Main execution function."""
    print("🐛 Bugninja Browser Automation")
    print("=" * 50)

    # Create rich terminal publisher
    rich_publisher = RichTerminalPublisher()
    event_manager = EventPublisherManager([rich_publisher])

    # Create client with event manager
    client = BugninjaClient(event_manager=event_manager, config=BugninjaConfig(headless=True))

    try:
        # Create task with all necessary parameters
        task = Task(
            description=BACPREP_NAVIGATION_PROMPT,
            max_steps=150,
            enable_healing=True,
            allowed_domains=["app.bacprep.ro"],
            secrets={
                "credential_email": os.getenv("BACPREP_MAIL_2"),
                "credential_password": os.getenv("BACPREP_LOGIN_PASSWORD_2"),
                "new_username": fake.name(),
            },
        )

        # Execute the task
        await client.parallel_run_tasks(task_list=[task, task])

        # if result.success:
        #     print("✅ Task completed successfully!")
        #     print(f"   Steps completed: {result.steps_completed}")
        #     print(f"   Execution time: {result.execution_time:.2f} seconds")
        #     print(f"   Traversal file: {result.traversal_file}")
        #     print(f"   Screenshots dir: {result.screenshots_dir}")
        # else:
        #     print(f"❌ Task failed: {result.error_message}")

    except Exception as e:
        print(f"❌ Task execution error: {e}")
        raise
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
