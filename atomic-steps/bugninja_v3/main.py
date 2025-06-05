import asyncio
from dotenv import load_dotenv
from pydantic import SecretStr
import os
from browser_use import Agent
from langchain_openai import AzureChatOpenAI

load_dotenv()

llm = AzureChatOpenAI(
    model="gpt-4o",
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    api_key=SecretStr(os.getenv("AZURE_OPENAI_KEY", "")),
)


async def main():
    agent = Agent(
        task="navigate to emag.ro search for wireless mice, select the two cheapest ones and add them to the cart, then go to the cart and check the total price",
        llm=llm,
    )
    await agent.run()


asyncio.run(main())
