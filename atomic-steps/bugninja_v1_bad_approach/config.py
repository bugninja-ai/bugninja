"""
Configuration module for BugNinja V1 prototype
Handles Azure OpenAI setup, environment variables, and constants
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from loguru import logger

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for BugNinja"""

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = "2024-05-01-preview"
    AZURE_MODEL_NAME = os.getenv("AZURE_MODEL_NAME", "gpt-4o")  # Default to GPT-4o

    # Browser Configuration
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "False").lower() == "true"
    BROWSER_CHANNEL = os.getenv("BROWSER_CHANNEL", "chrome")

    # Exploration Limits
    MAX_EXPLORATION_STEPS = int(os.getenv("MAX_EXPLORATION_STEPS", "100"))
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "./screenshots")
    STATES_DIR = os.getenv("STATES_DIR", "./states")

    # AI Behavior
    AI_TEMPERATURE = float(
        os.getenv("AI_TEMPERATURE", "0.1")
    )  # Low temperature for consistent decisions
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        logger.success("Configuration validation passed")


def get_azure_client():
    """Get configured Azure OpenAI client"""
    Config.validate_config()

    client = AzureOpenAI(
        azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
        api_key=Config.AZURE_OPENAI_API_KEY,
        api_version=Config.AZURE_OPENAI_API_VERSION,
    )

    logger.info("Azure OpenAI client initialized successfully")
    return client


def setup_logging():
    """Setup beautiful logging with loguru"""
    # Remove default handler
    logger.remove()

    # Add colorful console handler
    logger.add(
        sink=lambda message: print(message, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
    )

    # Add file handler
    logger.add(
        "./bugninja.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="10 MB",
    )

    logger.success("Logging setup complete")


# Initialize logging when module is imported
setup_logging()
