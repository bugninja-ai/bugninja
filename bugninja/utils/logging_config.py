import logging
import os
from typing import Any

# Set environment variables BEFORE any other imports to prevent telemetry
os.environ["BROWSER_USE_LOGGING_LEVEL"] = "critical"
os.environ["PLAYWRIGHT_LOGGING_LEVEL"] = "critical"
os.environ["LANGCHAIN_LOGGING_LEVEL"] = "critical"
os.environ["BROWSER_USE_TELEMETRY"] = "false"
os.environ["TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["BROWSER_USE_DISABLE_TELEMETRY"] = "true"
os.environ["DISABLE_TELEMETRY"] = "true"

# Custom Bugninja logging level
BUGNINJA_LOGGING_LEVEL: int = 35

# Check if logging is enabled via environment variable (read at module level)
LOGGING_ENABLED = os.getenv("BUGNINJA_LOGGING_ENABLED", "true").lower() == "true"

# Set actual level based on enabled/disabled
ACTUAL_LEVEL: int = BUGNINJA_LOGGING_LEVEL if LOGGING_ENABLED else 999

FORMAT: str = "%(asctime)s - %(message)s"


# Register custom logging level
logging.addLevelName(BUGNINJA_LOGGING_LEVEL, "BUGNINJA")


class BugninjaLogger(logging.Logger):
    """Custom logger class for Bugninja with additional logging methods.

    This logger extends the standard Python logger with a custom `bugninja_log`
    method that uses the BUGNINJA_LOGGING_LEVEL (35).
    """

    def bugninja_log(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message with the custom Bugninja logging level.

        Args:
            msg: The message to log
            *args: Additional arguments for string formatting
            **kwargs: Additional keyword arguments for logging
        """
        if self.isEnabledFor(BUGNINJA_LOGGING_LEVEL):
            self._log(BUGNINJA_LOGGING_LEVEL, msg, args, **kwargs)


# Register the custom logger class
logging.setLoggerClass(BugninjaLogger)


def configure_logging() -> None:
    """Configure logging based on BUGNINJA_LOGGING_ENABLED environment variable.

    This function:
    1. Sets the root logger to ACTUAL_LEVEL (BUGNINJA_LOGGING_LEVEL or 100)
    2. Configures all bugninja module loggers to ACTUAL_LEVEL
    3. Disables propagation to prevent interference
    """
    # Configure root logger
    logging.basicConfig(
        level=ACTUAL_LEVEL,
        format=FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration even if already configured
    )

    # Get the root logger and set its level
    root_logger = logging.getLogger()
    root_logger.setLevel(ACTUAL_LEVEL)

    # Remove all existing handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure all bugninja module loggers
    bugninja_modules = [
        "bugninja",
        "bugninja.api",
        "bugninja.agents",
        "bugninja.config",
        "bugninja.events",
        "bugninja.replication",
        "bugninja.schemas",
        "bugninja.utils",
        "bugninja_cli",
        "browser_use",
        "playwright",
        "langchain",
        "openai",
        "anthropic",
        "telemetry",
        "browser_use.telemetry",
        "browser_use.telemetry.telemetry",
        "browser_use.telemetry.telemetry.telemetry",
    ]

    for module in bugninja_modules:
        logger = logging.getLogger(module)

        # Set level based on logging enabled/disabled
        if LOGGING_ENABLED:
            logger.setLevel(ACTUAL_LEVEL)
        else:
            logger.setLevel(999)  # Disable all logging

        logger.propagate = False  # Prevent propagation to parent loggers

        # Remove any existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add a handler with proper formatter only if logging is enabled
        if LOGGING_ENABLED and not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)


# Configure logging when module is imported
configure_logging()

# Get the module logger (already configured in configure_logging)
logger: BugninjaLogger = logging.getLogger(__name__)  # type: ignore
