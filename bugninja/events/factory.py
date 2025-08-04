"""
Factory for creating event publishers.
"""

from typing import Any, Dict, List, Optional

from redis import Redis

from .base import EventPublisher
from .publishers import NullEventPublisher, RedisEventPublisher
from .types import EventPublisherType


def create_redis_client_from_config(config: Dict[str, Any]) -> Optional[Redis]:
    """Create Redis client from configuration.

    Args:
        config: Redis configuration dictionary

    Returns:
        Redis client if configuration is valid, None otherwise
    """
    try:
        return Redis(
            host=config.get("redis_host", "localhost"),
            port=config.get("redis_port", 6379),
            db=config.get("redis_db", 0),
            password=config.get("redis_password"),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    except Exception:
        return None


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

                elif publisher_type == EventPublisherType.REDIS:
                    redis_config = configs.get("redis", {})
                    redis_client = create_redis_client_from_config(redis_config)
                    if redis_client:
                        publishers.append(RedisEventPublisher(redis_client))
                    # Note: If Redis client creation fails, we skip this publisher
                    # instead of failing the entire factory
                # Future: elif publisher_type == EventPublisherType.RABBITMQ:
                # Future: elif publisher_type == EventPublisherType.KAFKA:

            except Exception:
                # Skip failed publishers instead of failing the entire factory
                continue

        return publishers
