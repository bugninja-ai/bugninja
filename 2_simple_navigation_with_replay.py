import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

# to generate a random fake name
fake = Faker()

METEOBLUE_NAVIGATION_PROMPT = """
Navigate to meteoblue.com, and search for New York City!
Access the settings, toggle temperature units twice (from Celsius → to Fahrenheit → and back to Celsius)!
""".strip()


async def simple_example() -> None:

    task = BugninjaTask(description=METEOBLUE_NAVIGATION_PROMPT)

    client = BugninjaClient()

    # Execute the task
    result = await client.run_task(task=task)

    if not result.traversal:
        raise Exception("Task execution failed")

    rich_print(list(result.traversal.brain_states.values())[-1])

    if not result.traversal_file:
        raise Exception("There is no saved traversal file")

    await client.replay_session(
        session=result.traversal_file, pause_after_each_step=True, enable_healing=False
    )


if __name__ == "__main__":
    asyncio.run(simple_example())
