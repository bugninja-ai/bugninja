# 🐛 Bugninja - AI-Powered Browser Automation & Self-Healing Framework

Bugninja is a sophisticated browser automation framework that combines AI agents with intelligent self-healing capabilities. It enables robust web testing, interaction recording, and automated task execution with built-in error recovery mechanisms.

## 🎯 Overview

Bugninja provides a complete ecosystem for AI-driven browser automation with three main components:

1. **🤖 AI Agents** - Intelligent agents that can navigate and interact with web applications
2. **📝 Action Recording** - Comprehensive logging of all browser interactions with DOM element data
3. **🩹 Self-Healing Replication** - Automated replay of recorded actions with intelligent error recovery

## 🏗️ Architecture

### Core Components

#### 1. **BugninjaAgentBase** (`src/agents/bugninja_agent_base.py`)
The foundation class that all agents inherit from, providing:
- **Hook System**: Lifecycle hooks for before/after actions and steps
- **Multi-Action Support**: Execute multiple actions in sequence
- **Error Handling**: Robust error recovery and retry mechanisms
- **State Management**: Comprehensive browser state tracking
- **Memory Integration**: Procedural memory for complex workflows

#### 2. **NavigatorAgent** (`src/agents/navigator_agent.py`)
A specialized agent for web navigation and task execution:
- **Action Recording**: Captures all interactions with detailed DOM element data
- **Brain State Tracking**: Records agent reasoning and decision-making
- **Traversal Persistence**: Saves complete session data to JSON files
- **Alternative Selectors**: Generates multiple XPath selectors for robust element identification

#### 3. **HealerAgent** (`src/agents/healer_agent.py`)
An intelligent recovery agent that can:
- **Self-Healing**: Automatically fix failed interactions
- **State Comparison**: Compare current state with expected states
- **Alternative Strategies**: Use different approaches when original actions fail
- **Seamless Integration**: Work alongside other agents for error recovery

#### 4. **BugninjaController** (`src/agents/extensions.py`)
Enhanced controller with additional browser actions:
- **Custom Scroll Actions**: Intelligent page scrolling with fallback mechanisms
- **Extended Action Support**: Additional browser interaction capabilities
- **Selector Fallbacks**: Multiple selector strategies for element identification

### Replication System

#### 5. **ReplicatorNavigator** (`src/replication/replicator_navigation.py`)
Base class for replaying recorded browser sessions:
- **Action Execution**: Replay recorded actions with intelligent fallbacks
- **Selector Strategies**: Multiple approaches for element identification
- **Error Recovery**: Built-in retry mechanisms for failed actions
- **User Interaction**: Pause and continue functionality for debugging

#### 6. **ReplicatorRun** (`src/replication/replicator_run.py`)
Advanced replication with self-healing capabilities:
- **State Machine**: Tracks progress through brain states
- **Automatic Healing**: Integrates HealerAgent for failed actions
- **State Comparison**: AI-powered evaluation of current vs expected states
- **Corrected Traversals**: Save successful replays with healing actions

## 🚀 Key Features

### 🤖 AI-Powered Navigation
- **Intelligent Decision Making**: Agents use LLMs to understand and execute complex tasks
- **Context Awareness**: Full browser state understanding for better decision making
- **Memory Integration**: Procedural memory for complex multi-step workflows
- **Adaptive Behavior**: Agents can adjust strategies based on page changes

### 📝 Comprehensive Recording
- **DOM Element Data**: Detailed information about every interacted element
- **Alternative Selectors**: Multiple XPath strategies for robust element identification
- **Brain State Tracking**: Complete agent reasoning and decision-making history
- **Action Metadata**: Timestamps, tokens, and performance metrics

### 🩹 Self-Healing Capabilities
- **Automatic Recovery**: Failed actions trigger intelligent healing mechanisms
- **State Comparison**: AI-powered evaluation of current vs expected states
- **Alternative Strategies**: Multiple approaches when original actions fail
- **Seamless Integration**: Healing happens transparently during replay

### 🔄 Robust Replication
- **Multiple Selector Strategies**: XPath, CSS, and relative selectors
- **Fallback Mechanisms**: Automatic retry with different approaches
- **User Control**: Pause, continue, and debug capabilities
- **Corrected Outputs**: Save successful replays with healing actions

## 📊 Data Structures

### Traversal Data
Each recorded session includes:
```json
{
  "test_case": "Original task description",
  "browser_config": "Browser profile settings",
  "secrets": "Sensitive data used during session",
  "brain_states": "Agent reasoning and decisions",
  "actions": "All interactions with DOM element data"
}
```

### Extended Actions
Each action includes:
- **Brain State ID**: Links action to agent reasoning
- **Action Data**: Original action parameters
- **DOM Element Data**: Detailed element information
- **Alternative Selectors**: Multiple XPath strategies

## 🛠️ Usage Examples

### Basic Navigation Agent
```python
from src.agents.navigator_agent import NavigatorAgent

# Create and run a navigation agent
agent = NavigatorAgent(
    task="Navigate to website and fill out form",
    llm=your_llm_model,
    browser_session=browser_session
)

# Run the agent (automatically saves traversal data)
await agent.run(max_steps=50)
```

### Self-Healing Replication
```python
from src.replication.replicator_run import ReplicatorRun

# Replay recorded session with self-healing
replicator = ReplicatorRun(
    json_path="traversals/traverse_20231201_143022_abc123.json",
    pause_after_each_step=True,
    sleep_after_actions=1.0
)

# Start replication (automatically handles failures with healer agent)
await replicator.start()
```

### Custom Healer Agent
```python
from src.agents.healer_agent import HealerAgent

# Create specialized healing agent
healer = HealerAgent(
    task="Complete failed form submission",
    llm=your_llm_model,
    browser_session=browser_session
)

# Run healing process
await healer.run(max_steps=10)
```

## 🔧 Configuration

### Browser Profile
```python
from browser_use import BrowserProfile

browser_profile = BrowserProfile(
    headless=False,
    slow_mo=100,
    viewport={"width": 1920, "height": 1080}
)
```

### Agent Settings
```python
agent_settings = {
    "use_vision": True,
    "planner_interval": 5,
    "save_conversation_path": "logs/conversation"
}
```

## 📁 File Structure
```
src/
├── agents/
│   ├── bugninja_agent_base.py    # Base agent class
│   ├── navigator_agent.py        # Navigation agent
│   ├── healer_agent.py          # Self-healing agent
│   └── extensions.py            # Enhanced controller
├── replication/
│   ├── replicator_navigation.py # Base replication
│   └── replicator_run.py        # Self-healing replication
├── models/
│   └── model_configs.py         # LLM configurations
├── schemas.py                   # Data models
└── utils/
    └── selector_factory.py      # XPath generation
```

## 🎯 Use Cases

### 🧪 Automated Testing
- **Regression Testing**: Replay recorded user sessions
- **Cross-Browser Testing**: Consistent behavior across browsers
- **Load Testing**: Automated user simulation
- **Accessibility Testing**: Automated compliance checking

### 🔄 Process Automation
- **Form Filling**: Automated data entry
- **Data Extraction**: Scraping with intelligent navigation
- **Workflow Automation**: Complex multi-step processes
- **Monitoring**: Automated health checks

### 🛠️ Development & Debugging
- **Bug Reproduction**: Reliable replay of user-reported issues
- **Performance Testing**: Automated performance regression detection
- **UI Testing**: Automated interface validation
- **Integration Testing**: End-to-end workflow validation

## 🔒 Security Features

- **Secret Management**: Secure handling of sensitive data
- **Isolated Sessions**: Clean browser state for each run
- **Error Isolation**: Failures don't affect subsequent runs
- **Audit Trail**: Complete logging of all actions

## 🚀 Getting Started

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Configure LLM**
   ```python
   from src.models.model_configs import azure_openai_model
   llm = azure_openai_model()
   ```

3. **Create Browser Session**
   ```python
   from browser_use import BrowserSession, BrowserProfile
   
   browser_session = BrowserSession(
       browser_profile=BrowserProfile(headless=False)
   )
   await browser_session.start()
   ```

4. **Run Your First Agent**
   ```python
   from src.agents.navigator_agent import NavigatorAgent
   
   agent = NavigatorAgent(
       task="Navigate to example.com and take a screenshot",
       llm=llm,
       browser_session=browser_session
   )
   
   await agent.run()
   ```

### 🛠️ Development Commands

The project includes several convenient development commands using Poetry:

```bash
# Run the main application
uv run python main.py

# Replay the last saved traversal
uv run python replay.py

# Lint and format the code
uv run ruff check --fix . && uv run isort . && uv run black . && uv run mypy main.py src

# Start Celery worker for task queuing
uv run celery -A celery_tasks worker --loglevel=INFO
```

## 🤝 Contributing

Bugninja is designed with extensibility in mind. Key areas for contribution:

- **New Agent Types**: Specialized agents for specific use cases
- **Enhanced Selectors**: Additional element identification strategies
- **Healing Strategies**: New approaches for error recovery
- **Performance Optimizations**: Faster execution and reduced resource usage


**Bugninja** - Where AI meets browser automation with intelligence and resilience! 🐛✨
