import asyncio

from bugninja import BugninjaTask
from bugninja.api.bugninja_pipeline import BugninjaPipeline, TaskSpec
from bugninja.schemas.test_case_io import TestCaseSchema


async def main() -> None:
    create_todo_list = BugninjaTask(
        start_url="https://freetodolist.com/dashboard",
        description="Login to FreeTodoList platform and create a TODO list with 5 items",
        extra_instructions=[
            "Login using credentials: cekijit723@ampdial.com / bugninja_test_2025",
            "Create a new list called 'TODOs' if one doesn't already exist",
            "Add exactly 5 different todo items to the list (make them realistic tasks)",
            "After adding all items, select one item randomly and extract its text as the output",
        ],
        io_schema=TestCaseSchema(
            output_schema={
                "SELECTED_ITEM": "Randomly selected item from the TODO list",
            }
        ),
    )

    delete_todo_item = BugninjaTask(
        start_url="https://freetodolist.com/dashboard",
        description="Login to FreeTodoList platform and delete the specified item from the TODO list",
        max_steps=60,
        extra_instructions=[
            "Login using credentials: cekijit723@ampdial.com / bugninja_test_2025",
            "Navigate to the 'TODOs' list that was created in the previous task",
            "Find and delete the specific item provided in the input schema",
            "Confirm the item has been successfully removed from the list",
        ],
        io_schema=TestCaseSchema(
            input_schema={
                "SELECTED_ITEM": "Item to be deleted from the TODO list",
            },
            output_schema={
                "DELETED_ITEM": "Item that was successfully deleted from the TODO list",
            },
        ),
    )

    await (
        BugninjaPipeline()
        .testcase("create_todo_list", TaskSpec(task=create_todo_list))
        .testcase("delete_todo_item", TaskSpec(task=delete_todo_item))
        .depends(
            "delete_todo_item",
            parents=["create_todo_list"],
        )
        .validate_io()
        .print_plan()
        .run(mode="auto")
    )


if __name__ == "__main__":
    asyncio.run(main())
