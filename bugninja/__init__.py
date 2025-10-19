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
6. **Multi-LLM Support** - Support for multiple AI providers (Azure, OpenAI, Anthropic, Google, DeepSeek, Ollama)

## Core Components

- `NavigatorAgent` - Primary browser automation agent
- `HealerAgent` - Self-healing intervention agent
- `ReplicatorRun` - Session replay with healing capabilities
- `BugninjaClient` - High-level API interface
- `EventPublisherManager` - Event tracking and monitoring
- `LLMProvider` - Enumeration of supported LLM providers
"""

# Core components
from bugninja.agents.navigator_agent import NavigatorAgent
from bugninja.agents.healer_agent import HealerAgent
from bugninja.replication.replicator_run import ReplicatorRun
from bugninja.api.bugninja_pipeline import BugninjaPipeline, TaskRef, TaskSpec
from bugninja.schemas.pipeline import Traversal, BugninjaBrowserConfig, BugninjaExtendedAction

from bugninja.config import (
    ConfigurationFactory,
    BugninjaSettings,
    LLMProvider,
    LLMConfig,
    ModelRegistry,
    create_llm_model_from_config,
    create_llm_config_from_settings,
)

import warnings


# High-level API
from bugninja.api import (
    BugninjaClient,
    BugninjaTask,
    BugninjaConfig,
    BugninjaError,
    TaskExecutionError,
    SessionReplayError,
    ConfigurationError,
    LLMError,
)

warnings.filterwarnings("ignore", category=DeprecationWarning, module="faiss.loader")
warnings.filterwarnings(
    "ignore", message="builtin type .* has no __module__ attribute", category=DeprecationWarning
)

__version__ = "0.1.2"
__all__ = [
    # Core components
    "NavigatorAgent",
    "HealerAgent",
    "ReplicatorRun",
    "Traversal",
    "BugninjaBrowserConfig",
    "BugninjaExtendedAction",
    # Configuration
    "ConfigurationFactory",
    "BugninjaSettings",
    "LLMProvider",
    "LLMConfig",
    "ModelRegistry",
    "create_llm_model_from_config",
    "create_llm_config_from_settings",
    # High-level API
    "BugninjaClient",
    "BugninjaTask",
    "BugninjaConfig",
    "BugninjaError",
    "TaskExecutionError",
    "SessionReplayError",
    "ConfigurationError",
    "LLMError",
    # BugninjaPipeline API
    "BugninjaPipeline",
    "TaskRef",
    "TaskSpec",
    "Dependency",
]
