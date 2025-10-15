import asyncio

from rich import print as rich_print

from bugninja.api.client import BugninjaClient
from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.schemas.models import BugninjaConfig, BugninjaTask


""" 
STEP 1: Navigate to temp-mail.org and get a temporary email
- Go to https://temp-mail.org/
- WAIT for the page to fully load and render all content
- Accept any cookie consents or popups if they appear
- Locate the generated temporary email address (usually prominently displayed)
- Remember this email address - you will need it later
- Do NOT close this tab
"""

MULTI_TAB_EMAIL_VERIFICATION_PROMPT = """
This is a complex multi-tab task that tests email verification workflow:


STEP 2: Sign up on freetodolist.com
- Navigate to https://freetodolist.com/signup
- WAIT for the signup page to fully load before interacting
- Fill out the signup form using:
  * Email: Use the temporary email from Step 1
  * Password: Generate a random password (e.g., "TestPass123!")
  * Confirm Password: Use the same password
- Click the "Sign Up" or "Create Account" button to submit the form
- WAIT for the signup process to complete

STEP 3: Verify welcome email received
- Switch back to the first tab (temp-mail.org)
- WAIT a few seconds for emails to arrive
- Check if a welcome/confirmation email from freetodolist.com has arrived in the inbox
- If the email is visible in the inbox, the task is successful
- If no email appears after waiting, try refreshing the temp-mail.org page and check again

STEP 4: Complete the task
- Once you verify the welcome email has arrived, the task is complete
- You can close the browser tabs

CRITICAL REQUIREMENTS:
- Always WAIT for pages to fully load before taking actions
- Keep both tabs open throughout the entire process
- The temporary email from Step 1 must be used exactly in Step 2
- Success is determined by receiving the welcome email in Step 3
- This tests multi-tab coordination and email verification workflows
""".strip()


async def multi_tab_email_verification_example() -> None:

    task = BugninjaTask(
        start_url="https://freetodolist.com/signup",
        description=MULTI_TAB_EMAIL_VERIFICATION_PROMPT,
    )

    # Execute the task
    result = await BugninjaClient(
        config=BugninjaConfig(
            viewport_width=1920, viewport_height=1080, video_recording=VideoRecordingConfig()
        )
    ).run_task(task=task)

    if result.error:
        raise Exception(result.error.message)

    if not result.traversal:
        rich_print(result)
        raise Exception("Task execution failed")

    rich_print(list(result.traversal.brain_states.values())[-1])


if __name__ == "__main__":
    asyncio.run(multi_tab_email_verification_example())
