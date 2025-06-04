import asyncio
from dotenv import load_dotenv
from browser_use import Agent
from langchain_openai import AzureChatOpenAI
from browser_use import Agent
from pydantic import SecretStr
import os
from rich import print as rich_print

load_dotenv()


async def main():
    # Read the task from the markdown file
    with open("./scenarios/emag_02_disrupted_purchase.md", "r") as f:
        task = f.read().strip()

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

    if AZURE_OPENAI_ENDPOINT is None or AZURE_OPENAI_KEY is None:
        raise ValueError(
            "Missing Azure OpenAI configuration. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
        )

    llm = AzureChatOpenAI(
        model="gpt-4.1",
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=SecretStr(AZURE_OPENAI_KEY),
    )

    agent = Agent(
        task=task,
        llm=llm,
    )
    await agent.run()

    print("###" * 10)

    for idx, (brain, model_taken_action, action_details) in enumerate(
        zip(
            agent.state.history.model_actions(),
            agent.state.history.model_thoughts(),
            agent.state.history.model_outputs(),
        )
    ):
        print(f"Step #{idx}")
        print("------")

        rich_print(brain)
        rich_print(model_taken_action)
        rich_print(action_details)
        rich_print("---" * 10)


if __name__ == "__main__":
    asyncio.run(main())
