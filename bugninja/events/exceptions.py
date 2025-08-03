"""
Exceptions for the event publishing system.
"""

from typing import Optional


class PublisherUnavailableError(Exception):
    """Raised when a publisher is not available for operations."""

    def __init__(self, message: str = "Publisher is not available"):
        self.message = message
        super().__init__(self.message)


class EventPublishingError(Exception):
    """Raised when event publishing fails."""

    def __init__(
        self, message: str = "Event publishing failed", publisher_name: Optional[str] = None
    ):
        self.message = message
        self.publisher_name = publisher_name
        super().__init__(self.message)
