import asyncio
import os

from dotenv import load_dotenv

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask

load_dotenv(dotenv_path="example_7.env")


async def secrets_scrolling_replay() -> None:
    task = BugninjaTask(
        start_url="https://www.imdb.com/",
        description="""Login using credentials. From the menu, select the option 'Top 250' movies.
        Scroll down to make the the 10th best movie visible, and click on it to open the details. In the details page scroll down and click on the awards the movie have won!""",
        secrets={
            "EMAIL_CREDENTIAL": os.getenv("EMAIL_CREDENTIAL"),
            "SECRET_CREDENTIAL": os.getenv("SECRET_CREDENTIAL"),
        },
        allowed_domains=["www.imdb.com"],
    )

    client = BugninjaClient()

    # Execute the task
    result = await client.run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if not result.traversal_file:
        raise Exception("Task execution failed; the `traversal_file` is empty")

    await client.replay_session(
        session=result.traversal_file,
        pause_after_each_step=False,
        enable_healing=False,
    )


if __name__ == "__main__":
    asyncio.run(secrets_scrolling_replay())
