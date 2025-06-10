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

    # ERROR    [agent] ⚠️⚠️⚠️ Agent(sensitive_data=••••••••) was provided but BrowserSession(allowed_domains=[...]) is not locked down! ⚠️⚠️⚠️
    # ☠️ If the agent visits a malicious website and encounters a prompt-injection attack, your sensitive_data may be exposed!

    email: str = "feligaf715@lewou.com"
    password: str = "9945504JA"
    new_username: str = "almafa"

    task: str = (
        "Go to bacprep.ro login to the platform with the provided credentials and edit the name of the user based on the provided information. If successful log out and close the browser."
    )

    agent = QuinoAgent(
        task=task,
        llm=llm,
        sensitive_data={
            "credential_email": email,
            "credential_password": password,
            "new_username": new_username,
        },
    )
    await agent.run()

    agent.save_q_agent_actions()


if __name__ == "__main__":
    asyncio.run(main())
