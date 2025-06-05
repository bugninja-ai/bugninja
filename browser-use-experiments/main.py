import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
from browser_use import Agent
from langchain_openai import AzureChatOpenAI
from browser_use import Agent
from pydantic import SecretStr
import os
from rich import print as rich_print
import json
from cuid2 import Cuid as CUID

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
    steps: Dict[str, Any] = {}

    for idx, (model_taken_action, brain, action_details) in enumerate(
        zip(
            agent.state.history.model_actions(),
            agent.state.history.model_thoughts(),
            agent.state.history.model_outputs(),
        )
    ):
        brain_dict = brain.model_dump()
        action_details_dict = action_details.model_dump()

        rich_print(f"Step {idx + 1}:")
        rich_print(f"Model Action:")
        rich_print(model_taken_action)
        rich_print(f"Brain:")
        rich_print(brain)
        rich_print(f"Action Details:")
        rich_print(action_details)

        steps |= {
            str(idx): {
                "model_taken_action": model_taken_action,
                "brain": brain_dict,
                "action_details": action_details_dict,
            }
        }

    # Create traversals directory if it doesn't exist
    os.makedirs("./traversals", exist_ok=True)

    # Generate a unique ID for this traversal
    traversal_id = CUID().generate()

    # Save the traversal data with the unique ID
    traversal_file = f"./traversals/{traversal_id}.json"
    with open(traversal_file, "w") as f:
        json.dump(steps, f, indent=2)

    print(f"Traversal saved with ID: {traversal_id}")


if __name__ == "__main__":
    asyncio.run(main())
