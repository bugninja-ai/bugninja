"""
Logging configuration utilities for Bugninja framework.

This module provides comprehensive logging configuration for the Bugninja framework,
including custom logging levels, telemetry suppression, and module-specific logging
configuration. It ensures clean, organized logging output while preventing telemetry
from third-party libraries.

## Key Components

1. **BugninjaLogger** - Custom logger class with Bugninja-specific logging methods
2. **configure_logging()** - Function to configure logging for all Bugninja modules
3. **Telemetry Suppression** - Environment variable setup to disable telemetry
4. **Custom Logging Level** - BUGNINJA_LOGGING_LEVEL (35) for framework-specific messages

## Usage Examples

```python
from bugninja.utils import logger, configure_logging

# Use custom logging
logger.bugninja_log("Custom log message")

# Configure logging (usually done automatically)
configure_logging()
```
"""

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
    method that uses the BUGNINJA_LOGGING_LEVEL (35). It provides a clean interface
    for Bugninja-specific logging messages.

    Example:
        ```python
        from bugninja.utils import logger

        # Use custom logging
        logger.bugninja_log("Custom log message")
        ```
    """

    def bugninja_log(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message with the custom Bugninja logging level.

        Args:
            msg (str): The message to log
            *args (Any): Additional arguments for string formatting
            **kwargs (Any): Additional keyword arguments for logging

        Example:
            ```python
            logger.bugninja_log("Processing action: %s", action_name)
            ```
        """
        if self.isEnabledFor(BUGNINJA_LOGGING_LEVEL):
            self._log(BUGNINJA_LOGGING_LEVEL, msg, args, **kwargs)


# Register the custom logger class
logging.setLoggerClass(BugninjaLogger)


def configure_logging() -> None:
    """Configure logging based on BUGNINJA_LOGGING_ENABLED environment variable.

    This function provides comprehensive logging configuration for the Bugninja framework:
    1. Sets the root logger to ACTUAL_LEVEL (BUGNINJA_LOGGING_LEVEL or 999)
    2. Configures all bugninja module loggers to ACTUAL_LEVEL
    3. Disables propagation to prevent interference
    4. Removes existing handlers to avoid duplicates
    5. Adds proper formatters for clean output

    The function is automatically called when the module is imported, but can be
    called manually to reconfigure logging if needed.

    Example:
        ```python
        from bugninja.utils import configure_logging

        # Manually configure logging (usually done automatically)
        configure_logging()
        ```
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
