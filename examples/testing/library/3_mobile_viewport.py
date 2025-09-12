import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaConfig, BugninjaTask

REDDIT_MOBILE_NAVIGATION_PROMPT = """
Navigate to ebay and search for home surveillance.
Order the list from cheapest to most expensive, and scroll down until the the result page options are visible.
Navigate to the second page of the results, and from the second page open the first product.
""".strip()

IPHONE_BROWSER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"


async def mobile_viewport() -> None:

    task = BugninjaTask(description=REDDIT_MOBILE_NAVIGATION_PROMPT)
    mobile_config = BugninjaConfig(
        viewport_height=844, viewport_width=390, user_agent=IPHONE_BROWSER_AGENT
    )

    client = BugninjaClient(config=mobile_config)

    # Execute the task
    result = await client.run_task(task=task)

    if not result.traversal:
        rich_print(result)
        raise Exception("Task execution failed")

    rich_print(list(result.traversal.brain_states.values())[-1])

    if not result.traversal_file:
        raise Exception("There is no saved traversal file")

    await client.replay_session(
        session=result.traversal_file, pause_after_each_step=False, enable_healing=False
    )


if __name__ == "__main__":
    asyncio.run(mobile_viewport())
