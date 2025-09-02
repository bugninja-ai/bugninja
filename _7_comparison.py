import asyncio

from browser_use import Agent
from rich import print as rich_print

from bugninja.config.llm_creator import (
    create_llm_config_from_settings,
    create_llm_model_from_config,
)

agent = Agent(
    task="""Navigate to https://www.reddit.com, login using credentials stored as environment secrets, navigate to the Quality Assurance subreddit.
        Scroll down to locate the 10th post, and finally click on it to open the post details""",
    sensitive_data={
        "EMAIL_CREDENTIAL": "cikkolekka@necub.com",
        "SECRET_CREDENTIAL": "bugninja_2025",
    },
    llm=create_llm_model_from_config(create_llm_config_from_settings()),
)


async def main():
    history = await agent.run(max_steps=100)

    for h in history.history:
        h.state.screenshot = None

    rich_print(history)


if __name__ == "__main__":
    asyncio.run(main())
