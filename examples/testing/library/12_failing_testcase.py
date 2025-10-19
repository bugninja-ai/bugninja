import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask, HTTPAuthCredentials

HTTP_AUTH_PROMPT = """
Navigate to the authentication page and check whether the HTTP basic authentication process succeeded. 
The task is successful when you can see the text 'You are authenticated' on the page. In any other case the test should fail.
""".strip()


async def failing_testcase() -> None:

    # Create HTTP authentication credentials
    http_auth = HTTPAuthCredentials(username="failing_username", password="failing_password")

    task = BugninjaTask(
        start_url="https://testpages.eviltester.com/styled/auth/basic-auth-results.html",
        description=HTTP_AUTH_PROMPT,
        http_auth=http_auth,
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if not result.traversal:
        rich_print(result)
        raise Exception("Task execution failed")

    # Check if authentication was successful by looking at the final brain state
    final_brain_state = list(result.traversal.brain_states.values())[-1]

    rich_print("\n--- Final Brain State ---")
    rich_print(final_brain_state)


if __name__ == "__main__":
    asyncio.run(failing_testcase())
