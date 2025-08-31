import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaConfig, BugninjaTask

REDDIT_MOBILE_NAVIGATION_PROMPT = """
Navigate to reddit.com, open hamburger menu, open the first subreddit and click on the first post.
""".strip()

IPHONE_BROWSER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"


async def mobile_viewport() -> None:

    task = BugninjaTask(description=REDDIT_MOBILE_NAVIGATION_PROMPT)
    mobile_config = BugninjaConfig(
        viewport_height=844, viewport_width=390, user_agent=IPHONE_BROWSER_AGENT
    )

    # Execute the task
    result = await BugninjaClient(config=mobile_config).run_task(task=task)

    rich_print(result)


if __name__ == "__main__":
    asyncio.run(mobile_viewport())
