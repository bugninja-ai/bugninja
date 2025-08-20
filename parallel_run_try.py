"""
Main execution script for Bugninja browser automation tasks.

This script demonstrates how to use the Bugninja high-level API for
browser automation tasks with proper configuration and error handling.
"""

import asyncio
import os

from dotenv import load_dotenv
from faker import Faker

# Import the new high-level API
from bugninja.api import BugninjaClient, BugninjaTask
from bugninja.api.models import BugninjaConfig
from bugninja.config import ConfigurationFactory
from bugninja.events import EventPublisherManager
from bugninja.events.publishers.rich_terminal_publisher import RichTerminalPublisher

# Initialize faker for generating test data
fake = Faker()

# Load environment variables
load_dotenv()

# Get settings for authentication prompt
settings = ConfigurationFactory.get_settings()


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
        # Create first task with BACPREP_MAIL_1
        task1 = BugninjaTask(
            description=BACPREP_NAVIGATION_PROMPT,
            max_steps=150,
            enable_healing=True,
            allowed_domains=["app.bacprep.ro"],
            secrets={
                "credential_email": os.getenv("BACPREP_MAIL_1"),
                "credential_password": os.getenv("BACPREP_LOGIN_PASSWORD_1"),
                "new_username": fake.name(),
            },
        )

        # Create second task with BACPREP_MAIL_2
        task2 = BugninjaTask(
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

        print("🚀 Starting mixed execution with 2 BACPREP tasks")
        print(f"📧 Task 1: {os.getenv('BACPREP_MAIL_1', 'N/A')}")
        print(f"📧 Task 2: {os.getenv('BACPREP_MAIL_2', 'N/A')}")
        print("⚙️ Max concurrent: 1 (sequential execution)")
        print("-" * 50)

        # Execute two tasks with different credentials using new mixed execution
        result = await client.parallel_run_mixed(
            executions=[task1, task2], max_concurrent=2, enable_healing=True  # Sequential execution
        )

        # Display results
        print("-" * 50)
        print("📊 Execution Results:")
        print(f"✅ Total tasks: {result.total_tasks}")
        print(f"✅ Successful: {result.successful_tasks}")
        print(f"❌ Failed: {result.failed_tasks}")
        print(f"⏱️ Total execution time: {result.total_execution_time:.2f} seconds")

        if result.overall_success:
            print("🎉 All tasks completed successfully!")
        else:
            print("⚠️ Some tasks failed. Check individual results for details.")

    except Exception as e:
        print(f"❌ BugninjaTask execution error: {e}")
        raise
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
