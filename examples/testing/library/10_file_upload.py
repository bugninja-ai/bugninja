import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask, FileUploadInfo

BLACK_AND_WHITE_PROMPT = """
Go to resizepixel.com and upload an image file.
Convert that image file into a black and white format. If done, do not download the file but stop the task.
""".strip()


async def file_upload_example() -> None:

    task = BugninjaTask(
        start_url="https://www.resizepixel.com/convert-image-to-black-white/",
        description=BLACK_AND_WHITE_PROMPT,
        available_files=[
            FileUploadInfo(
                name="bunny.webp",
                path="../testing/assets/bunny.webp",
                description="an image about a bunny",
            )
        ],
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if not result.traversal:
        rich_print(result)
        raise Exception("Task execution failed")

    rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(file_upload_example())
