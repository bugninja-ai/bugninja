"""
Bugninja Replication - Browser interaction replay and self-healing

This module provides classes for replaying recorded browser interactions
with intelligent error recovery and self-healing capabilities.
"""

from .replicator_run import ReplicatorRun
from .replicator_navigation import ReplicatorNavigator, ReplicatorError

__all__ = [
    "ReplicatorRun",
    "ReplicatorNavigator",
    "ReplicatorError",
]
