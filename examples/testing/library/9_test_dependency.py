import asyncio

from bugninja import BugninjaTask
from bugninja.api.bugninja_pipeline import BugninjaPipeline, TaskSpec
from bugninja.schemas.test_case_io import TestCaseSchema


async def main() -> None:
    amazon_price = BugninjaTask(
        start_url="https://www.amazon.com/",
        description="We will search for a book called 'Of Mice and Men' on Amazon",
        extra_instructions=[
            "Search for the book 'Of Mice and Men'",
            "Extract the FIRST price of the book from the search results.",
        ],
        io_schema=TestCaseSchema(
            output_schema={
                "BOOK_PRICE": "First price of the book on Amazon",
            }
        ),
    )

    ebay_price = BugninjaTask(
        start_url="https://www.ebay.com/",
        description="We will search for a book called 'Of Mice and Men' on Ebay",
        max_steps=60,
        extra_instructions=[
            "Search for the book 'Of Mice and Men'",
            "Extract the FIRST price of the book from the search results.",
        ],
        io_schema=TestCaseSchema(
            input_schema={
                "BOOK_PRICE": "First price of the book on Amazon",
            },
            output_schema={
                "BOOK_AMAZON_PRICE": "First price of the book on Amazon",
                "BOOK_EBAY_PRICE": "First price of the book on Ebay",
            },
        ),
    )

    await (
        BugninjaPipeline()
        .testcase("amazon_price", TaskSpec(task=amazon_price))
        .testcase("ebay_price", TaskSpec(task=ebay_price))
        .depends(
            "ebay_price",
            parents=["amazon_price"],
        )
        .validate_io()
        .print_plan()
        .run(mode="auto")
    )


if __name__ == "__main__":
    asyncio.run(main())
