"""
Custom exception hierarchy for Bugninja API.

This module provides a **comprehensive exception hierarchy** for handling
different types of errors that can occur during browser automation tasks.

## Exception Hierarchy

1. **BugninjaError** - Base exception for all operations
2. **TaskExecutionError** - Task execution failures
3. **SessionReplayError** - Session replay failures
4. **ConfigurationError** - Configuration validation errors
5. **LLMError** - Language model operation errors
6. **BrowserError** - Browser automation errors
7. **ValidationError** - Input validation errors

## Usage Examples

```python
from bugninja.api.exceptions import (
    BugninjaError, TaskExecutionError, SessionReplayError
)

try:
    result = await client.run_task(task)
except TaskExecutionError as e:
    print(f"Task failed: {e.message}")
    print(f"Steps completed: {e.steps_completed}")
except SessionReplayError as e:
    print(f"Replay failed: {e.message}")
    print(f"Session file: {e.session_file}")
```
"""

from typing import Any, Dict, Optional


class BugninjaError(Exception):
    """Base exception for all Bugninja operations.

    This is the **root exception class** that all other Bugninja exceptions
    inherit from. It provides a common interface for error handling with
    comprehensive error details and context information.

    Attributes:
        message (str): Human-readable error message
        details (Dict[str, Any]): Additional error details for debugging
        original_error (Optional[Exception]): Original exception that caused this error

    Example:
        ```python
        try:
            # Some Bugninja operation
            pass
        except BugninjaError as e:
            print(f"Error: {e.message}")
            print(f"Details: {e.details}")
            if e.original_error:
                print(f"Original: {e.original_error}")
        ```
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize BugninjaError with comprehensive error information.

        Args:
            message (str): Human-readable error message
            details (Optional[Dict[str, Any]]): Additional error details for debugging
            original_error (Optional[Exception]): Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_error = original_error

    def __str__(self) -> str:
        """Return formatted error message with details if available.

        Returns:
            str: Formatted error message with optional details
        """
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class TaskExecutionError(BugninjaError):
    """Raised when task execution fails.

    This exception is raised when a browser automation task cannot be
    completed successfully, either due to technical issues or task
    requirements that cannot be met.

    Attributes:
        task_description (Optional[str]): Description of the task that failed
        steps_completed (int): Number of steps completed before failure

    Example:
        ```python
        try:
            result = await client.run_task(task)
        except TaskExecutionError as e:
            print(f"Task '{e.task_description}' failed after {e.steps_completed} steps")
            print(f"Error: {e.message}")
        ```
    """

    def __init__(
        self,
        message: str,
        task_description: Optional[str] = None,
        steps_completed: int = 0,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize TaskExecutionError with task-specific information.

        Args:
            message (str): Error message describing the failure
            task_description (Optional[str]): Description of the task that failed
            steps_completed (int): Number of steps completed before failure
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the failure
        """
        super().__init__(message, details, original_error)
        self.task_description = task_description
        self.steps_completed = steps_completed


class SessionReplayError(BugninjaError):
    """Raised when session replay fails.

    This exception is raised when attempting to replay a recorded
    browser session fails, typically due to changes in the target
    website or technical issues.

    Attributes:
        session_file (Optional[str]): Path to the session file that failed
        step_number (Optional[int]): Step number where replay failed

    Example:
        ```python
        try:
            result = await client.replay_session(session_file)
        except SessionReplayError as e:
            print(f"Replay of {e.session_file} failed at step {e.step_number}")
            print(f"Error: {e.message}")
        ```
    """

    def __init__(
        self,
        message: str,
        session_file: Optional[str] = None,
        step_number: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize SessionReplayError with session-specific information.

        Args:
            message (str): Error message describing the replay failure
            session_file (Optional[str]): Path to the session file that failed
            step_number (Optional[int]): Step number where replay failed
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the failure
        """
        super().__init__(message, details, original_error)
        self.session_file = session_file
        self.step_number = step_number


class ConfigurationError(BugninjaError):
    """Raised when configuration is invalid.

    This exception is raised when the Bugninja configuration is
    invalid or missing required settings.

    Attributes:
        config_field (Optional[str]): Name of the configuration field that is invalid
        expected_value (Optional[str]): Expected value for the configuration field
        actual_value (Optional[str]): Actual value that was provided

    Example:
        ```python
        try:
            client = BugninjaClient(config=invalid_config)
        except ConfigurationError as e:
            print(f"Config field '{e.config_field}' is invalid")
            print(f"Expected: {e.expected_value}, Got: {e.actual_value}")
        ```
    """

    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize ConfigurationError with configuration-specific information.

        Args:
            message (str): Error message describing the configuration issue
            config_field (Optional[str]): Name of the configuration field that is invalid
            expected_value (Optional[str]): Expected value for the configuration field
            actual_value (Optional[str]): Actual value that was provided
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.config_field = config_field
        self.expected_value = expected_value
        self.actual_value = actual_value


class LLMError(BugninjaError):
    """Raised when LLM operations fail.

    This exception is raised when there are issues with the Language
    Model, such as API errors, authentication failures, or model
    unavailability.

    Attributes:
        llm_provider (Optional[str]): Name of the LLM provider that failed
        llm_model (Optional[str]): Name of the LLM model that failed
        api_response (Optional[Dict[str, Any]]): Response from the LLM API (if available)

    Example:
        ```python
        try:
            result = await client.run_task(task)
        except LLMError as e:
            print(f"LLM provider '{e.llm_provider}' failed with model '{e.llm_model}'")
            print(f"API response: {e.api_response}")
        ```
    """

    def __init__(
        self,
        message: str,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        api_response: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize LLMError with LLM-specific information.

        Args:
            message (str): Error message describing the LLM failure
            llm_provider (Optional[str]): Name of the LLM provider that failed
            llm_model (Optional[str]): Name of the LLM model that failed
            api_response (Optional[Dict[str, Any]]): Response from the LLM API (if available)
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.api_response = api_response


class BrowserError(BugninjaError):
    """Raised when browser operations fail.

    This exception is raised when there are issues with the browser
    automation, such as element not found, navigation failures, or
    browser crashes.

    Attributes:
        browser_action (Optional[str]): Action that was being performed
        element_selector (Optional[str]): Selector of the element that failed
        page_url (Optional[str]): URL of the page where the error occurred

    Example:
        ```python
        try:
            result = await client.run_task(task)
        except BrowserError as e:
            print(f"Browser action '{e.browser_action}' failed")
            print(f"Element: {e.element_selector}")
            print(f"Page: {e.page_url}")
        ```
    """

    def __init__(
        self,
        message: str,
        browser_action: Optional[str] = None,
        element_selector: Optional[str] = None,
        page_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize BrowserError with browser-specific information.

        Args:
            message (str): Error message describing the browser failure
            browser_action (Optional[str]): Action that was being performed
            element_selector (Optional[str]): Selector of the element that failed
            page_url (Optional[str]): URL of the page where the error occurred
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.browser_action = browser_action
        self.element_selector = element_selector
        self.page_url = page_url


class ValidationError(BugninjaError):
    """Raised when input validation fails.

    This exception is raised when user input or configuration
    fails validation checks.

    Attributes:
        field_name (Optional[str]): Name of the field that failed validation
        field_value (Optional[str]): Value that failed validation
        validation_rule (Optional[str]): Rule that was violated

    Example:
        ```python
        try:
            task = BugninjaTask(description="")  # Empty description
        except ValidationError as e:
            print(f"Field '{e.field_name}' failed validation")
            print(f"Value: {e.field_value}")
            print(f"Rule: {e.validation_rule}")
        ```
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[str] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize ValidationError with validation-specific information.

        Args:
            message (str): Error message describing the validation failure
            field_name (Optional[str]): Name of the field that failed validation
            field_value (Optional[str]): Value that failed validation
            validation_rule (Optional[str]): Rule that was violated
            details (Optional[Dict[str, Any]]): Additional error details
            original_error (Optional[Exception]): Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule
