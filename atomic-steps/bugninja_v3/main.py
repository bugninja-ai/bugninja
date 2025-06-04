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
        task="navigate to bacprep.ro and log in using imetstamas@gmail.com and lolxd123 and then complete a section 3 Type test with a proper text input and then evaulauate it to see the scores, for the input you must generate a proper text input according to the interface instructions you see",
        llm=llm,
    )
    await agent.run()


asyncio.run(main())
