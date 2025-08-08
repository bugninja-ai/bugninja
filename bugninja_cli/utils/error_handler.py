"""
Error handling utilities for Bugninja CLI.

This module provides intelligent error handling with contextual
suggestions for recovery.
"""

from typing import Dict, Optional

import click

from bugninja.api.models import BugninjaErrorType, BugninjaTaskError

from ..themes.colors import echo_error, echo_info, echo_warning


class ErrorSuggestionProvider:
    """Provides contextual suggestions for different error types."""

    def get_suggestion(self, error: BugninjaTaskError) -> str:
        """Get contextual suggestion for error recovery.

        Args:
            error: Error object to analyze

        Returns:
            Suggestion string for recovery
        """
        match error.error_type:
            case BugninjaErrorType.BROWSER_ERROR:
                return "Try running with --healing-enabled or --headless mode"
            case BugninjaErrorType.SESSION_REPLAY_ERROR:
                return "Re-record the session or use --enable-healing"
            case BugninjaErrorType.LLM_ERROR:
                return "Check your API credentials and network connection"
            case BugninjaErrorType.VALIDATION_ERROR:
                return "Verify your task file format and required fields"
            case BugninjaErrorType.CONFIGURATION_ERROR:
                return "Check your configuration settings and environment variables"
            case BugninjaErrorType.TASK_EXECUTION_ERROR:
                return "Review task description and check for invalid actions"
            case BugninjaErrorType.CLEANUP_ERROR:
                return "Check system resources and browser session state"
            case _:
                return "Check the documentation or run with --verbose for details"

    def get_recovery_options(self, error: BugninjaTaskError) -> Dict[str, str]:
        """Get available recovery options for an error.

        Args:
            error: Error object to analyze

        Returns:
            Dictionary of recovery options
        """
        options = {}

        match error.error_type:
            case BugninjaErrorType.BROWSER_ERROR:
                options = {
                    "1": "Retry with healing enabled",
                    "2": "Retry with headless mode",
                    "3": "Retry with different browser settings",
                    "4": "Show detailed error information",
                }
            case BugninjaErrorType.SESSION_REPLAY_ERROR:
                options = {
                    "1": "Retry with healing enabled",
                    "2": "Re-record the session",
                    "3": "Skip failed steps",
                    "4": "Show detailed error information",
                }
            case BugninjaErrorType.LLM_ERROR:
                options = {
                    "1": "Check API credentials",
                    "2": "Verify network connection",
                    "3": "Try different LLM provider",
                    "4": "Show detailed error information",
                }
            case _:
                options = {
                    "1": "Retry operation",
                    "2": "Show detailed error information",
                    "3": "Check documentation",
                }

        return options


def display_error_with_suggestions(error: BugninjaTaskError, show_recovery: bool = False) -> None:
    """Display error with intelligent suggestions.

    Args:
        error: Error object to display
        show_recovery: Whether to show recovery options
    """
    provider = ErrorSuggestionProvider()

    # Display error information
    echo_error(f"❌ Operation failed: {error.message}")
    click.echo(f"   Error Type: {error.error_type.value}")

    # Display suggestion
    suggestion = provider.get_suggestion(error)
    echo_info(f"   Suggestion: {suggestion}")

    # Display additional details
    if error.details:
        click.echo("   Error Details:")
        for key, value in error.details.items():
            click.echo(f"     {key}: {value}")

    if error.original_error:
        click.echo(f"   Original Error: {error.original_error}")

    # Show recovery options if requested
    if show_recovery:
        display_recovery_options(error)


def display_recovery_options(error: BugninjaTaskError) -> None:
    """Display interactive recovery options.

    Args:
        error: Error object to get recovery options for
    """
    provider = ErrorSuggestionProvider()
    options = provider.get_recovery_options(error)

    echo_warning("\n⚠️  Recovery Options:")
    for key, description in options.items():
        click.echo(f"   {key}. {description}")

    click.echo("   0. Exit")


def handle_error_interactively(error: BugninjaTaskError) -> Optional[str]:
    """Handle error with interactive recovery.

    Args:
        error: Error object to handle

    Returns:
        Selected recovery option or None to exit
    """
    display_error_with_suggestions(error, show_recovery=True)

    provider = ErrorSuggestionProvider()
    options = provider.get_recovery_options(error)

    while True:
        try:
            choice = click.prompt(
                "\nEnter choice", type=click.Choice(list(options.keys()) + ["0"]), default="0"
            )

            if choice == "0":
                return None

            return options[choice]

        except click.Abort:
            return None


def validate_task_file(file_path: str) -> None:
    """Validate task file before execution.

    Args:
        file_path: Path to task file

    Raises:
        click.BadParameter: If file is invalid
    """
    import os

    if not os.path.exists(file_path):
        raise click.BadParameter(f"Task file does not exist: {file_path}")

    if not file_path.endswith(".md"):
        raise click.BadParameter(f"Task file must be a markdown file: {file_path}")

    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise click.BadParameter(f"Task file is empty: {file_path}")

    if file_size > 1024 * 1024:  # 1MB limit
        raise click.BadParameter(f"Task file is too large: {file_path}")


def validate_session_file(file_path: str) -> None:
    """Validate session file before replay.

    Args:
        file_path: Path to session file

    Raises:
        click.BadParameter: If file is invalid
    """
    import json
    import os

    if not os.path.exists(file_path):
        raise click.BadParameter(f"Session file does not exist: {file_path}")

    if not file_path.endswith(".json"):
        raise click.BadParameter(f"Session file must be a JSON file: {file_path}")

    # Check if file is valid JSON
    try:
        with open(file_path, "r") as f:
            json.load(f)
    except json.JSONDecodeError:
        raise click.BadParameter(f"Session file is not valid JSON: {file_path}")


def validate_bulk_files(file_paths: list[str], file_type: str = "task") -> None:
    """Validate multiple files for bulk operations.

    Args:
        file_paths: List of file paths to validate
        file_type: Type of files ("task" or "session")

    Raises:
        click.BadParameter: If any file is invalid
    """
    if len(file_paths) < 2:
        raise click.BadParameter(f"Bulk operations require at least 2 {file_type} files")

    for file_path in file_paths:
        if file_type == "task":
            validate_task_file(file_path)
        else:
            validate_session_file(file_path)


def handle_validation_error(error: Exception, context: str = "") -> None:
    """Handle validation errors with user-friendly messages.

    Args:
        error: Validation error to handle
        context: Context where the error occurred
    """
    if isinstance(error, click.BadParameter):
        echo_error(f"❌ Validation Error: {error.message}")
        if context:
            echo_info(f"   Context: {context}")
    else:
        echo_error(f"❌ Unexpected Error: {str(error)}")
        if context:
            echo_info(f"   Context: {context}")

    echo_info("   Use --help for more information about valid options")
