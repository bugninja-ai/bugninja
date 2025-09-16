"""
Utility functions and classes for Bugninja CLI.

This module provides **comprehensive utility functions and classes** for:
- project initialization and validation
- project structure management
- configuration file handling
- CLI styling and formatting
- task management and execution
- project validation and information display

## Key Components

1. **initialization** - Project setup and configuration utilities
2. **project_validator** - Project validation and information display
3. **style** - CLI styling and formatting utilities
4. **task_manager** - Task creation, validation, and management
5. **task_executor** - Task execution and orchestration

## Usage Examples

```python
from bugninja_cli.utils.initialization import is_bugninja_project, get_project_root
from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.task_manager import TaskManager
from bugninja_cli.utils.task_executor import TaskExecutor

# Check if current directory is a Bugninja project
if is_bugninja_project():
    print("Valid Bugninja project found")

# Get project root directory
project_root = get_project_root()

# Use decorator to require valid project
@require_bugninja_project
def my_command(project_root: Path):
    # Command logic here
    pass

# Create and manage tasks
task_manager = TaskManager(project_root)
task_id = task_manager.create_task("My Task")

# Execute tasks
executor = TaskExecutor(config, project_root)
result = await executor.execute_task(task_info)
```
"""
