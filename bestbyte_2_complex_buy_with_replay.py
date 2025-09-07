import asyncio

from faker import Faker
from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask

# to generate a random fake name
fake = Faker()

BESTBYTE_PRODUCT_PURCHASE_PROMPT = f"""
A returning user logs in, browses multiple categories, applies filters, adds multiple items to cart, and checks out.

Expected Behavior:
- System correctly handles login.
- Filters narrow down products; appropriate items added.
- Cart updates item quantities accurately.
- Transaction completes and confirmation appears.
""".strip()

instructions = [
    "Go to https://bestbyte.hu/demo and click “Bejelentkezés/Regisztráció”.",
    "Log in with valid credentials.",
    "From product categories select 'Mobil, Okosóra' subcategory, and select samsung phones",
    "Add the first mobile phone to the cart.",
    "In the product categories, select 'Laptop' subcategory, and in that, select Gamer laptops",
    "Apply the cheapest first ordering filter.",
    "Add the first laptop to the cart.",
    "Go to the cart to ensure that both items listed.",
    "Modify quantity of the smartphone to 2.",
    "Since we are on the demo site, clicking on the Proceed button will result in logging out of the website. If this happens, consider the traversal complete.",
]


LOGIN_EMAIL = "gehad90115@cspaus.com"
LOGIN_PASSWORD = "test_bestbyte_2025"


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
