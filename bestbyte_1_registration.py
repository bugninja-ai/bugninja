import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

# to generate a random fake name

BEST_BYTE_REGISTRATION_PROMPT = f"""
A new user signs up, logs out and logs back in with the appropriate credentials!

**Expected Behavior:**

- Registration completes without errors.
- Login works with new credentials.
""".strip()


async def simple_navigation() -> None:

    fake = Faker()

    task = BugninjaTask(
        description=BEST_BYTE_REGISTRATION_PROMPT,
        extra_instructions=[
            "Navigate to the https://bestbyte.hu/demo/",
            "Click “Bejelentkezés/Regisztráció” (Login/Register) link.",
            "Fill out the registration form (e-mail, password, personal details).",
            "Submit the form and verify successful registration.",
            "Log out (if automatically logged in, log out first).",
            "Log back in with the newly created credentials.",
        ],
        secrets={
            "REGISTRATION_EMAIL": fake.email(),
            "REGISTRATION_PASSWORD": fake.password(),
            "REGISTRATION_PHONE_NUMBER": "+36304053519",
            "REGISTRATION_STREET_ADDRESS": "Angyal utca 21.",
            "REGISTRATION_CITY": "Budapest",
            "REGISTRATION_POSTAL_CODE": "1094",
            # ----
            "USER_FIRST_NAME": fake.first_name(),
            "USER_LAST_NAME": fake.last_name(),
        },
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(simple_navigation())
