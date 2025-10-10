import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask
from bugninja.schemas.test_case_io import TestCaseSchema

# to generate a random fake name
fake = Faker()

BACPREP_NAVIGATION_PROMPT = f"""
Login to the platform via email authentication with the provided credentials:

email: feligaf715@lewou.com
password: 9945504JA

Edit the name of the user to '{fake.name()}'! 
If successful log out and close the browser!
""".strip()


async def simple_navigation() -> None:
    # Create task with I/O schema for data extraction
    task = BugninjaTask(
        start_url="https://app.bacprep.ro/en",
        description=BACPREP_NAVIGATION_PROMPT,
        io_schema=TestCaseSchema(
            output_schema={
                "PREVIOUS_USERNAME": "previous name of the user before the update",
                "NEW_USERNAME": "new username of the user after the update",
            }
        ),
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    # Display results
    if result.traversal:
        # Show extracted data if available
        if hasattr(result.traversal, "extracted_data") and result.traversal.extracted_data:
            rich_print("📊 Extracted Data:")
            rich_print(
                f"• Previous Username: {result.traversal.extracted_data.get('PREVIOUS_USERNAME', 'N/A')}"
            )
            rich_print(
                f"• New Username: {result.traversal.extracted_data.get('NEW_USERNAME', 'N/A')}"
            )
        else:
            rich_print("⚠️ No data was extracted from this task")

        # Show final brain state
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(simple_navigation())
