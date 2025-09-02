import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask


async def secrets_scrolling_replay() -> None:
    task = BugninjaTask(
        description="""Navigate to https://www.reddit.com, login using credentials stored as environment secrets, navigate to the Quality Assurance subreddit.
        Scroll down to locate the 10th post, and finally click on it to open the post details""",
        secrets={"EMAIL_CREDENTIAL": "cikkolekka@necub.com", "SECRET_CREDENTIAL": "bugninja_2025"},
        allowed_domains=["https://www.reddit.com"],
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(secrets_scrolling_replay())
