"""
Replication error classes.

This module contains all exception classes used in the replication system,
providing centralized error handling and better code organization.
"""


class ReplicatorError(Exception):
    """Base exception for ReplicatorRun errors."""

    pass


class ActionError(ReplicatorError):
    """Exception raised when browser actions fail."""

    pass


class SelectorError(ReplicatorError):
    """Exception raised when selector operations fail."""

    pass


class NavigationError(ReplicatorError):
    """Exception raised when navigation operations fail."""

    pass


class BrowserError(ReplicatorError):
    """Exception raised when browser operations fail."""

    pass


class ConfigurationError(ReplicatorError):
    """Exception raised when configuration is invalid."""

    pass


class ValidationError(ReplicatorError):
    """Exception raised when data validation fails."""

    pass
