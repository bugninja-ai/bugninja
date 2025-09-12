import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask


def corrupt_traversal_file(traversal_file_path: Path, action_to_corrupt: str) -> Path:
    with open(traversal_file_path, "r") as f:
        saved_json_str: str = f.read()

    json_data: Dict[str, Any] = json.loads(saved_json_str)

    #! we purposefully remove the `xpath` and `alternative_relative_xpaths` keys in order to simulate a failing interaction, or changed UI

    dom_of_second_action: Dict[str, Any] = json_data["actions"][action_to_corrupt][
        "dom_element_data"
    ]
    dom_of_second_action["xpath"] = ""
    dom_of_second_action["alternative_relative_xpaths"] = []
    json_data["actions"][action_to_corrupt]["dom_element_data"] = dom_of_second_action

    #! save the corrupted traversal
    with open(traversal_file_path, "w") as f:
        f.write(json.dumps(json_data, indent=4, ensure_ascii=False))

    return traversal_file_path


WIKIPEDIA_NAVIGATION_PROMPT = """
Navigate to wikipedia.com and search for Artificial Intelligence, and them open the first article.
""".strip()


async def self_healing() -> None:

    task = BugninjaTask(description=WIKIPEDIA_NAVIGATION_PROMPT)
    client = BugninjaClient()

    # Execute the task
    result = await client.run_task(task=task)

    if not result.traversal_file:
        raise Exception("Task execution failed for some reason; the `traversal_file` is empty")

    #! let's artificially corrupt the traversal
    corrupted_file_path: Path = corrupt_traversal_file(
        result.traversal_file, action_to_corrupt="action_2"
    )

    replay_with_healing_result = await client.replay_session(
        session=corrupted_file_path, enable_healing=True
    )

    rich_print(replay_with_healing_result)


if __name__ == "__main__":
    asyncio.run(self_healing())
