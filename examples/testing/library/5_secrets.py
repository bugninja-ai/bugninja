import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.schemas.models import BugninjaTask

LOGIN_PRACTICE_PROMPT = """
With the provided credentials, try to log in!
Verify the successful login, and after that log out and close the browser!
""".strip()


async def secrets() -> None:
    task = BugninjaTask(
        start_url="https://practicetestautomation.com/practice-test-login/",
        description=LOGIN_PRACTICE_PROMPT,
        #! secrets stored this way are not visible by the model directly
        secrets={"EMAIL_SECRET": "student", "PASSWORD_SECRET": "Password123"},
        #! when we are using secrets, it is also beneficial to provide the allowed domains,
        #! so the agent NEVER navigates to malicious sites
        allowed_domains=["practicetestautomation.com"],
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(secrets())
