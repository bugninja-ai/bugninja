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


AUTHENTICATION_HANDLING_EXTRA_PROMPT: str = (
    """
### HANDLING THIRD PARTY AUTHENTICATION

It is very important that you are able to handle third-party authentication or the non-authentication software, such as applications or SMS verifications, in your action space. There is a declared action for this type of interaction, and you must not forget that you can handle this. In this scenario, you will wait for the user's response, and the user will be signaling when the third-party authentication is completed. After that is done, you must re-evaluate the updated state of the browser.
""".strip()
)


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
        extend_planner_system_message=AUTHENTICATION_HANDLING_EXTRA_PROMPT,
    )

    await agent.run()


BACPREP_NAVIGATION_PROMPT = """
Go to app.bacprep.ro/en, login to the platform via email authentication with the 
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


ERSTE_NAVIGATION_PROMPT = """
1. Go to george.erstebank.hu and login to the platform with the e-channel ID and the e-channel password! IMPORTANT: There might be two factor authentication be present on the web application. Do not panic, the user will be with you for this interaction, therefore you should not close the flow at this point, just wait until the user finishes the authentication process!
2. Go to the profile section by clicking on the profile image button next to the 'Kijelentkezés' button!
3. Switch the language of the website ONCE! If it is 'English' switch to 'Hungarian', and if it is 'Hungarian' switch to 'English'!
4. Log out of the portal!
5. Close the browser!
""".strip()


async def erste_navigation() -> None:

    await run_agent(
        task=ERSTE_NAVIGATION_PROMPT,
        secrets={
            "e_channel_id": os.getenv("E_CHANNEL_ID"),
            "e_channel_password": os.getenv("E_CHANNEL_PASSWORD"),
        },
        allowed_domains=[
            "george.erstebank.hu",
            "erstebank.hu",
            "login.erstebank.hu",
            "www.erstebank.hu",
        ],
    )


if __name__ == "__main__":
    asyncio.run(bacprep_navigation())
