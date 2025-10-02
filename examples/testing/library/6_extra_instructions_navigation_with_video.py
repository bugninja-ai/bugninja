import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.schemas.models import BugninjaConfig, BugninjaTask


async def extra_rules_navigation() -> None:
    task = BugninjaTask(
        description='Navigate to Amazon homepage, search for "wireless headphones", browse through product listings',
        extra_instructions=[
            "Open exactly three different(!) product pages after each other",
            "On the product's page read its average score",
            "Compare scores across all three products",
            "Navigate back to previously viewed products if necessary",
            "Add the product with the best single average score to the cart",
        ],
    )

    # Execute the task with video recording, using the default Bugninja config with the default video recording config
    result = await BugninjaClient(
        config=BugninjaConfig(video_recording=VideoRecordingConfig())
    ).run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(extra_rules_navigation())
