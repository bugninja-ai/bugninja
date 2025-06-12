import asyncio
import os

from browser_use import BrowserProfile
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from src.custom_agent import QuinoAgent
from pathlib import Path
import base64

load_dotenv()


async def capture_screenshot_hook(agent: QuinoAgent):
    """Hook function that captures screenshots at each step"""

    if agent.browser_session.agent_current_page is None:
        return

    # Take a screenshot of the current page
    screenshot_b64 = await agent.browser_session.take_screenshot()

    # Get current step information
    current_url = (await agent.browser_session.get_current_page()).url
    step_count = len(agent.state.history.model_actions())

    # Save screenshot to file
    screenshot_folder = Path("./screenshots")
    screenshot_folder.mkdir(exist_ok=True)

    # Convert base64 to PNG and save
    screenshot_path = screenshot_folder / f"step_{step_count}_{current_url.replace('/', '_')}.png"
    with open(screenshot_path, "wb") as f:
        f.write(base64.b64decode(screenshot_b64))

    print(f"Screenshot saved: {screenshot_path}")


async def main() -> None:

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

    if AZURE_OPENAI_ENDPOINT is None or AZURE_OPENAI_KEY is None:
        raise ValueError(
            "Missing Azure OpenAI configuration. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
        )

    # ERROR    [agent] ⚠️⚠️⚠️ Agent(sensitive_data=••••••••) was provided but BrowserSession(allowed_domains=[...]) is not locked down! ⚠️⚠️⚠️
    # ☠️ If the agent visits a malicious website and encounters a prompt-injection attack, your sensitive_data may be exposed!

    email: str = "feligaf715@lewou.com"
    password: str = "9945504JA"
    new_username: str = "almafa"

    task: str = (
        "Go to app.bacprep.ro login to the platform with the provided credentials and edit the name of the user based on the provided information. If successful log out and close the browser."
    )

    agent = QuinoAgent(
        task=task,
        llm=AzureChatOpenAI(
            model="gpt-4.1",
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=SecretStr(AZURE_OPENAI_KEY),
            temperature=0.001,
        ),
        sensitive_data={
            "credential_email": email,
            "credential_password": password,
            "new_username": new_username,
        },
        # TODO! test what strict selectors do
        browser_profile=BrowserProfile(strict_selectors=True),
    )
    await agent.run(
        # on_step_start=capture_screenshot_hook,  # Capture at start of each step
    )

    agent.save_q_agent_actions()


if __name__ == "__main__":
    asyncio.run(main())
