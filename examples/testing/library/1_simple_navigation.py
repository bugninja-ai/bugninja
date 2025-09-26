import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask

# to generate a random fake name
fake = Faker()

BACPREP_NAVIGATION_PROMPT = f"""
Go to app.bacprep.ro/en, login to the platform via email authentication with the 
provided credentials:

email: feligaf715@lewou.com
password: 9945504JA

Edit the name of the user to '{fake.name()}'! 
If successful log out and close the browser!
""".strip()


async def simple_navigation() -> None:
    task = BugninjaTask(description=BACPREP_NAVIGATION_PROMPT)

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(simple_navigation())
