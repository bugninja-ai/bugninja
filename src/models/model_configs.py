import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

load_dotenv()


# TODO!: create a proper config oriented and well documented factory method here


def azure_openai_model(temperature: float = 0.001) -> AzureChatOpenAI:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

    if AZURE_OPENAI_ENDPOINT is None or AZURE_OPENAI_KEY is None:
        raise ValueError(
            "Missing Azure OpenAI configuration. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
        )

    return AzureChatOpenAI(
        model="gpt-4.1",
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=SecretStr(AZURE_OPENAI_KEY),
        temperature=temperature,
    )
