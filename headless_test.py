import asyncio
import os

from browser_use import Agent, BrowserProfile
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

load_dotenv()

llm = AzureChatOpenAI(
    model="gpt-4.1",
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    api_key=SecretStr(os.getenv("AZURE_OPENAI_KEY", "")),
)


task_prompt = """
Navigate to ebay and search for home surveillance.
Order the list from cheapest to most expensive, and scroll down until the the result page options are visible.
Navigate to the second page of the results, and from the second page open the first product.
"""


async def main():
    agent = Agent(task=task_prompt, llm=llm, browser_profile=BrowserProfile(headless=False))
    await agent.run(max_steps=100)


if __name__ == "__main__":
    asyncio.run(main())
