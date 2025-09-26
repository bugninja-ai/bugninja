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
6. **replay_metadata** - Replay run metadata management
7. **run_metadata** - AI-navigated run metadata management
8. **task_lookup** - Task lookup and identification utilities
9. **result_display** - Result display and formatting utilities

## Usage Examples

```python
from bugninja_cli.utils.initialization import is_bugninja_project, get_project_root
from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.task_manager import TaskManager
from bugninja_cli.utils.task_executor import TaskExecutor
from bugninja_cli.utils.replay_metadata import update_task_metadata_with_replay
from bugninja_cli.utils.run_metadata import update_task_metadata_with_ai_run
from bugninja_cli.utils.task_lookup import get_task_by_identifier
from bugninja_cli.utils.result_display import display_task_success, display_task_failure

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

# Update replay metadata
update_task_metadata_with_replay(task_toml_path, traversal_path, result, healing_enabled)
```
"""
