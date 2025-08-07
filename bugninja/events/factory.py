"""
Factory for creating event publishers.
"""

from typing import Any, Dict, List

from .base import EventPublisher
from .publishers import NullEventPublisher
from .types import EventPublisherType


class EventPublisherFactory:
    """Factory for creating event publishers with explicit configuration."""

    @staticmethod
    def create_publishers(
        publisher_types: List[EventPublisherType], configs: Dict[str, Any]
    ) -> List[EventPublisher]:
        """Create multiple event publishers with explicit configuration.

        Args:
            publisher_types: List of publisher types to create
            configs: Configuration for publishers

        Returns:
            List of event publisher instances
        """
        publishers: List[EventPublisher] = []

        for publisher_type in publisher_types:
            try:
                if publisher_type == EventPublisherType.NULL:
                    publishers.append(NullEventPublisher())

                    # Note: If Redis client creation fails, we skip this publisher
                    # instead of failing the entire factory
                # Future: elif publisher_type == EventPublisherType.RABBITMQ:
                # Future: elif publisher_type == EventPublisherType.KAFKA:

            except Exception:
                # Skip failed publishers instead of failing the entire factory
                continue

        return publishers
