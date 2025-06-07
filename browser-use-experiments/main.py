import asyncio
import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from src.custom_agent import QuinoAgent

load_dotenv()


async def main() -> None:

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
        temperature=0.05,
    )

    task: str = (
        "Go to Bestbyte.hu website, search for bluetooth mices and click on search button. After the mices list is displayed, scroll down to the last element on the page. Open it's link, and close the browser"
    )

    agent = QuinoAgent(
        task=task,
        llm=llm,
    )
    await agent.run()

    agent.save_q_agent_actions()


if __name__ == "__main__":
    asyncio.run(main())
