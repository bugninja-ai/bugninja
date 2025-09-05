import asyncio
import os

from dotenv import load_dotenv
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

load_dotenv(dotenv_path="example_8.env")


async def advanced_interactions_replay() -> None:
    task = BugninjaTask(
        description="Navigate to Google Sheets, login using the account credentials stored as environment secrets, create a new spreadsheet and follow the additional instructions",
        extra_instructions=[
            'Create a new blank spreadsheet with title "Currency Converter"',
            'Set up cell A1 with header name "USD Amount" and A2 with a static value of 1000',
            'Set up column B1 with header name "HUF Amount"',
            "In cell B2, enter a formula to convert USD to Hungarian Forint (multiply by current exchange rate)",
            "Save the spreadsheet before completing the test",
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
