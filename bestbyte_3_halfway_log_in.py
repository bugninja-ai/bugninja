import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

# to generate a random fake name
fake = Faker()

BESTBYTE_PRODUCT_PURCHASE_PROMPT = f"""
A user browses, searches for something, then logs in halfway through to purchase.

Expected Behavior:
- Returns relevant products.
- Attempting to add to cart as guest prompts login or registration.
- Login preserves cart state (product stays in cart).
- Checkout proceeds after login.
- Since we are on the demo site, clicking on the Proceed button will result in logging out of the website. If this happens, consider the traversal complete.
""".strip()

instructions = [
    "Visit https://bestbyte.hu/demo website",
    "From product categories select 'Mobil, Okosóra' subcategory, and select Samsung phones",
    "Scroll down until the last product is visible on the page and click on it.",
    "Click “Kosárba tesz” on product page.",
    "System will likely prompt login/register since the user is not authenticated at this point",
    "Choose to login with the provided credentials: fill and submit the form.",
    "After login, return to cart.",
    "Continue with checkout: choose payment/shipping.",
]


LOGIN_EMAIL = "gehad90115@cspaus.com"
LOGIN_PASSWORD = "test_bestbyte_2025"

#! this testcase fails, but for some reason it should pass


async def simple_navigation() -> None:
    task = BugninjaTask(
        description=BESTBYTE_PRODUCT_PURCHASE_PROMPT,
        extra_instructions=instructions,
        secrets={"LOGIN_EMAIL": LOGIN_EMAIL, "LOGIN_PASSWORD": LOGIN_PASSWORD},
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(simple_navigation())
