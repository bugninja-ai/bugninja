import asyncio
import base64
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from browser_use import BrowserProfile  # type: ignore
from dotenv import load_dotenv
from faker import Faker

from src.agents.navigator_agent import NavigatorAgent
from src.models.model_configs import azure_openai_model

fake = Faker()


load_dotenv()


async def capture_screenshot_hook(agent: NavigatorAgent) -> None:
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


async def run_agent(
    task: str, allowed_domains: List[str], secrets: Optional[Dict[str, Any]] = None
) -> None:

    agent = NavigatorAgent(
        task=task,
        llm=azure_openai_model(),
        sensitive_data=secrets,
        browser_profile=BrowserProfile(
            strict_selectors=True,
            # ? these None settings are necessary in order for every new run to be perfectly independent and clean
            user_data_dir=None,
            storage_state=None,
            allowed_domains=allowed_domains,
        ),
    )

    # on_step_start=capture_screenshot_hook,  # Capture at start of each step

    await agent.run()


BACPREP_NAVIGATION_PROMPT = """
Go to app.bacprep.ro login to the platform via email authentication with the 
provided credentials and edit the name of the user based on the provided information. 
If successful log out and close the browser.
""".strip()


async def bacprep_navigation() -> None:

    await run_agent(
        task=BACPREP_NAVIGATION_PROMPT,
        secrets={
            "credential_email": "feligaf715@lewou.com",
            "credential_password": os.getenv("BACPREP_LOGIN_PASSWORD"),
            "new_username": fake.name(),
        },
        allowed_domains=["app.bacprep.ro"],
    )


if __name__ == "__main__":
    asyncio.run(bacprep_navigation())
