"""
Bugninja CLI - Command-line interface for browser automation.

This module provides a **comprehensive command-line interface** for:
- project initialization and management
- task creation and management
- task execution and monitoring
- session replay and healing
- statistics and reporting

## Key Components

1. **add** - Task creation and management
2. **init** - Project initialization and setup
3. **run** - Task execution and automation
4. **replay** - Session replay with healing
5. **stats** - Statistics and reporting

## Usage Examples

```bash
# Initialize a new project
bugninja init --name my-automation-project

# Create a new task
bugninja add --name "Login Flow"

# Run a specific task
bugninja run --task login-flow

# Replay a recorded session
bugninja replay --traversal session_123

# View project statistics
bugninja stats --list
```
"""
