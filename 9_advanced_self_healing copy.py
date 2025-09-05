import asyncio
import os

from dotenv import load_dotenv
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

load_dotenv(dotenv_path="example_9.env")


async def advanced_interactions_replay() -> None:
    task = BugninjaTask(
        description="Navigate to Trello, login using credentials and create a new board with custom instructions",
        extra_instructions=[
            "Create a new board titled 'QA Testing Board'",
            "Add three lists: 'To Do', 'In Progress', 'Done'",
            "Create cards in 'To Do' list: 'Write test cases', 'Execute tests', 'Report bugs'",
            "Move the first card to 'In Progress' list",
            "Add a due date to the moved card",
        ],
        secrets={
            "EMAIL_CREDENTIAL": os.getenv("EMAIL_CREDENTIAL"),
            "PASSWORD_CREDENTIAL": os.getenv("PASSWORD_CREDENTIAL"),
        },
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(advanced_interactions_replay())
