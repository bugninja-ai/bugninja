"""
Replication error classes for Bugninja framework.

This module contains all exception classes used in the replication system,
providing centralized error handling and better code organization. These
exceptions are used throughout the replication process to handle various
failure scenarios during session replay.

## Exception Hierarchy

```
ReplicatorError (base)
├── ActionError
├── SelectorError
├── NavigationError
├── BrowserError
├── ConfigurationError
└── ValidationError
```

## Usage Examples

```python
from bugninja.replication.errors import (
    ReplicatorError,
    ActionError,
    SelectorError,
    NavigationError,
    BrowserError,
    ConfigurationError,
    ValidationError
)

try:
    # Some replication operation
    pass
except ActionError as e:
    print(f"Action failed: {e}")
except SelectorError as e:
    print(f"Selector operation failed: {e}")
except ReplicatorError as e:
    print(f"General replication error: {e}")
```
"""


class ReplicatorError(Exception):
    """Base exception for all replication-related errors.

    This is the base exception class for all errors that can occur during
    the replication process. All other replication exceptions inherit from
    this class.

    Example:
        ```python
        try:
            # Some replication operation
            pass
        except ReplicatorError as e:
            print(f"Replication error: {e}")
        ```
    """

    pass


class ActionError(ReplicatorError):
    """Exception raised when browser actions fail.

    This exception is raised when a specific browser action (click, type, etc.)
    fails during the replication process.

    Example:
        ```python
        try:
            # Perform browser action
            pass
        except ActionError as e:
            print(f"Action failed: {e}")
        ```
    """

    pass


class SelectorError(ReplicatorError):
    """Exception raised when selector operations fail.

    This exception is raised when element selection operations fail,
    such as when a selector cannot find the target element.

    Example:
        ```python
        try:
            # Find element by selector
            pass
        except SelectorError as e:
            print(f"Selector failed: {e}")
        ```
    """

    pass


class NavigationError(ReplicatorError):
    """Exception raised when navigation operations fail.

    This exception is raised when page navigation operations fail,
    such as when a page cannot be loaded or navigated to.

    Example:
        ```python
        try:
            # Navigate to page
            pass
        except NavigationError as e:
            print(f"Navigation failed: {e}")
        ```
    """

    pass


class BrowserError(ReplicatorError):
    """Exception raised when browser operations fail.

    This exception is raised when general browser operations fail,
    such as browser initialization or browser-level errors.

    Example:
        ```python
        try:
            # Browser operation
            pass
        except BrowserError as e:
            print(f"Browser error: {e}")
        ```
    """

    pass


class ConfigurationError(ReplicatorError):
    """Exception raised when configuration is invalid.

    This exception is raised when the replication configuration
    is invalid or missing required parameters.

    Example:
        ```python
        try:
            # Validate configuration
            pass
        except ConfigurationError as e:
            print(f"Configuration error: {e}")
        ```
    """

    pass


class ValidationError(ReplicatorError):
    """Exception raised when data validation fails.

    This exception is raised when data validation fails during
    the replication process, such as when traversal data is invalid.

    Example:
        ```python
        try:
            # Validate data
            pass
        except ValidationError as e:
            print(f"Validation error: {e}")
        ```
    """

    pass
