"""
Custom exception hierarchy for Bugninja API.

This module provides a comprehensive exception hierarchy for handling
different types of errors that can occur during browser automation tasks.

## Exception Hierarchy

1. **BugninjaError** - Base exception for all operations
2. **TaskExecutionError** - Task execution failures
3. **SessionReplayError** - Session replay failures
4. **ConfigurationError** - Configuration validation errors
5. **LLMError** - Language model operation errors
6. **BrowserError** - Browser automation errors
7. **ValidationError** - Input validation errors
"""

from typing import Any, Dict, Optional


class BugninjaError(Exception):
    """Base exception for all Bugninja operations.

    This is the root exception class that all other Bugninja exceptions
    inherit from. It provides a common interface for error handling.

    ## Attributes

    1. **message** - Human-readable error message
    2. **details** - Additional error details for debugging
    3. **original_error** - Original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize BugninjaError.

        Args:
            message: Human-readable error message
            details: Additional error details for debugging
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_error = original_error

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class TaskExecutionError(BugninjaError):
    """Raised when task execution fails.

    This exception is raised when a browser automation task cannot be
    completed successfully, either due to technical issues or task
    requirements that cannot be met.

    ## Attributes

    1. **task_description** - Description of the task that failed
    2. **steps_completed** - Number of steps completed before failure
    """

    def __init__(
        self,
        message: str,
        task_description: Optional[str] = None,
        steps_completed: int = 0,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize TaskExecutionError.

        Args:
            message: Error message describing the failure
            task_description: Description of the task that failed
            steps_completed: Number of steps completed before failure
            details: Additional error details
            original_error: Original exception that caused the failure
        """
        super().__init__(message, details, original_error)
        self.task_description = task_description
        self.steps_completed = steps_completed


class SessionReplayError(BugninjaError):
    """Raised when session replay fails.

    This exception is raised when attempting to replay a recorded
    browser session fails, typically due to changes in the target
    website or technical issues.

    ## Attributes

    1. **session_file** - Path to the session file that failed
    2. **step_number** - Step number where replay failed
    """

    def __init__(
        self,
        message: str,
        session_file: Optional[str] = None,
        step_number: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize SessionReplayError.

        Args:
            message: Error message describing the replay failure
            session_file: Path to the session file that failed
            step_number: Step number where replay failed
            details: Additional error details
            original_error: Original exception that caused the failure
        """
        super().__init__(message, details, original_error)
        self.session_file = session_file
        self.step_number = step_number


class ConfigurationError(BugninjaError):
    """Raised when configuration is invalid.

    This exception is raised when the Bugninja configuration is
    invalid or missing required settings.

    ## Attributes

    1. **config_field** - Name of the configuration field that is invalid
    2. **expected_value** - Expected value for the configuration field
    3. **actual_value** - Actual value that was provided
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
        """Initialize ConfigurationError.

        Args:
            message: Error message describing the configuration issue
            config_field: Name of the configuration field that is invalid
            expected_value: Expected value for the configuration field
            actual_value: Actual value that was provided
            details: Additional error details
            original_error: Original exception that caused the error
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

    ## Attributes

    1. **llm_provider** - Name of the LLM provider that failed
    2. **llm_model** - Name of the LLM model that failed
    3. **api_response** - Response from the LLM API (if available)
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
        """Initialize LLMError.

        Args:
            message: Error message describing the LLM failure
            llm_provider: Name of the LLM provider that failed
            llm_model: Name of the LLM model that failed
            api_response: Response from the LLM API (if available)
            details: Additional error details
            original_error: Original exception that caused the error
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

    ## Attributes

    1. **browser_action** - Action that was being performed
    2. **element_selector** - Selector of the element that failed
    3. **page_url** - URL of the page where the error occurred
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
        """Initialize BrowserError.

        Args:
            message: Error message describing the browser failure
            browser_action: Action that was being performed
            element_selector: Selector of the element that failed
            page_url: URL of the page where the error occurred
            details: Additional error details
            original_error: Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.browser_action = browser_action
        self.element_selector = element_selector
        self.page_url = page_url


class ValidationError(BugninjaError):
    """Raised when input validation fails.

    This exception is raised when user input or configuration
    fails validation checks.

    ## Attributes

    1. **field_name** - Name of the field that failed validation
    2. **field_value** - Value that failed validation
    3. **validation_rule** - Rule that was violated
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
        """Initialize ValidationError.

        Args:
            message: Error message describing the validation failure
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_rule: Rule that was violated
            details: Additional error details
            original_error: Original exception that caused the error
        """
        super().__init__(message, details, original_error)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule
