import asyncio

from dotenv import load_dotenv
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

load_dotenv(dotenv_path="example_9.env")


async def advanced_interactions_replay() -> None:
    task = BugninjaTask(
        description="Navigate to https://parabank.parasoft.com/, login using credentials and perform banking operations with the custom instructions",
        extra_instructions=[
            "Login and navigate to transfer funds section",
            "Add a new contact with full details (name, account number, bank details)",
            "Transfer $500 to the newly added contact",
            "Verify the transaction in transaction history",
        ],
        secrets={
            "EMAIL_CREDENTIAL": "test_account",
            "PASSWORD_CREDENTIAL": "password_123",
            # -------- NEW CONTACT DETAILS -------
            "NEW_CONTACT_NAME": "Jonathan Doeson",
            "NEW_CONTACT_ACCOUNT_NUMBER": "123456789",
            "NEW_CONTACT_BANK_DETAILS": "123 Main St, Anytown, USA",
        },
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(advanced_interactions_replay())
