"""
Bugninja - AI-Powered Browser Automation & Self-Healing Framework

A sophisticated browser automation framework that combines **AI agents** with intelligent
**self-healing capabilities** for robust web testing, interaction recording, and automated
task execution with built-in error recovery mechanisms.

## Key Features

1. **AI-Powered Navigation** - Natural language task descriptions
2. **Self-Healing Replay** - Automatic test adaptation and recovery
3. **Session Recording** - Complete interaction traversal capture
4. **Event Tracking** - Comprehensive operation monitoring
5. **Modular Architecture** - Extensible and maintainable design

## Core Components

- `NavigatorAgent` - Primary browser automation agent
- `HealerAgent` - Self-healing intervention agent
- `ReplicatorRun` - Session replay with healing capabilities
- `BugninjaClient` - High-level API interface
- `EventPublisherManager` - Event tracking and monitoring
"""

# Core components
from .agents.navigator_agent import NavigatorAgent
from .agents.healer_agent import HealerAgent
from .replication.replicator_run import ReplicatorRun
from .schemas.pipeline import Traversal, BugninjaBrowserConfig, BugninjaExtendedAction
from .models.model_configs import azure_openai_model
from .config import ConfigurationFactory, BugninjaSettings

# High-level API
from .api import (
    BugninjaClient,
    BugninjaTask,
    BugninjaConfig,
    BugninjaError,
    TaskExecutionError,
    SessionReplayError,
    ConfigurationError,
    LLMError,
)

__version__ = "0.1.0"
__all__ = [
    # Core components
    "NavigatorAgent",
    "HealerAgent",
    "ReplicatorRun",
    "Traversal",
    "BugninjaBrowserConfig",
    "BugninjaExtendedAction",
    "azure_openai_model",
    "ConfigurationFactory",
    "BugninjaSettings",
    # High-level API
    "BugninjaClient",
    "BugninjaTask",
    "BugninjaConfig",
    "BugninjaError",
    "TaskExecutionError",
    "SessionReplayError",
    "ConfigurationError",
    "LLMError",
]
