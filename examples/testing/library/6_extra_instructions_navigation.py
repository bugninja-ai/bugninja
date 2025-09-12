import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.api.models import BugninjaTask


async def extra_rules_navigation() -> None:
    task = BugninjaTask(
        description='Navigate to Amazon homepage, search for "wireless headphones", browse through product listings',
        extra_instructions=[
            "Open exactly three separate products’ pages after each other"
            "On the product’s page read its average rating",
            "Compare ratings quality across all three products",
            "Navigate back to previously viewed products if necessary",
            "Add the product with the best single user review to the cart",
        ],
    )

    # Execute the task
    result = await BugninjaClient().run_task(task=task)

    if result.traversal:
        rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(extra_rules_navigation())
