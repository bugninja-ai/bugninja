import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask


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


async def comprehensive_test() -> None:
    task = BugninjaTask(
        start_url="https://parabank.parasoft.com/",
        description="Login using credentials and perform banking operations with the custom instructions",
        extra_instructions=[
            "Login to the website using the provided credentials",
            "Go to 'Open new account' section",
            "Create a new 'CHECKING' account and a 'SAVINGS' account",
            "Go to transfer funds section of the website",
            "Move 75$ from the first account to a different account",
            "Verify the transaction in 'Accounts Overview' and check whether the appropriate funds are available on the created accounts",
            "Log out of the platform",
        ],
        secrets={
            # ? credentials here are placeholder, since the website is for only demo purposes
            "USERNAME": "test_account_username",
            "PASSWORD": "password_123",
        },
    )

    client = BugninjaClient()

    # Execute the task
    result = await client.run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if not result.traversal_file:
        rich_print(result)
        raise Exception("Task execution failed")

    await client.replay_session(
        session=result.traversal_file,
        pause_after_each_step=False,
        enable_healing=False,
    )

    #! let's artificially corrupt the traversal
    corrupt_traversal_file(traversal_file_path=result.traversal_file, action_to_corrupt="action_7")

    await client.replay_session(
        session=result.traversal_file,
        pause_after_each_step=False,
        enable_healing=True,
    )


if __name__ == "__main__":
    asyncio.run(comprehensive_test())
