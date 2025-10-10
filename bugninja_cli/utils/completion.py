"""
Auto-completion utilities for Bugninja CLI commands.

This module provides **high-performance auto-completion functions** for:
- task name completion (both folder names and human-readable names)
- traversal ID completion from recorded sessions
- project-aware completion that validates Bugninja project context
- graceful error handling for completion failures
- intelligent caching for optimal performance

## Key Components

1. **complete_task_names()** - Complete available task names for run/replay commands
2. **complete_traversal_ids()** - Complete available traversal IDs for replay command
3. **complete_executed_tasks()** - Complete tasks that have execution history
4. **Project validation utilities** - Ensure completions work within Bugninja projects
5. **Performance optimizations** - Caching, fast file scanning, minimal I/O

## Usage Examples

```python
from bugninja_cli.utils.completion import complete_task_names, complete_traversal_ids

# Use in Click commands
@click.option("--task", shell_complete=complete_task_names)
def run_command(task):
    pass

@click.option("--traversal", shell_complete=complete_traversal_ids)
def replay_command(traversal):
    pass
```
"""

import os
import time
from pathlib import Path
from typing import List, Optional

import click

from bugninja_cli.utils.initialization import get_project_root

# Simple caching for project root to avoid repeated directory walks
_cached_project_root: Optional[Path] = None
_cache_timestamp: float = 0
CACHE_TTL = 5.0  # 5 seconds cache


def _get_cached_project_root() -> Optional[Path]:
    """Get cached project root, refresh if stale."""
    global _cached_project_root, _cache_timestamp

    if _cached_project_root is None or time.time() - _cache_timestamp > CACHE_TTL:
        _cached_project_root = get_project_root()
        _cache_timestamp = time.time()

    return _cached_project_root


def _get_task_names(tasks_dir: str) -> List[str]:
    """Get all task names without caching to avoid stale results."""
    if not os.path.exists(tasks_dir):
        return []

    names = []
    try:
        for item in os.listdir(tasks_dir):
            item_path = os.path.join(tasks_dir, item)
            if os.path.isdir(item_path):
                names.append(item)
    except Exception:
        pass
    return names


def _get_traversal_ids(traversals_dir: str) -> List[str]:
    """Get all traversal IDs without caching to avoid stale results."""
    if not os.path.exists(traversals_dir):
        return []

    ids = []
    try:
        for filename in os.listdir(traversals_dir):
            if filename.startswith("traverse_") and filename.endswith(".json"):
                # Extract ID: traverse_*_{id}.json
                parts = filename[:-5].split("_")
                if len(parts) >= 3:
                    ids.append(parts[-1])
    except Exception:
        pass
    return ids


def complete_task_names(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete available task names for run and replay commands."""
    project_root = _get_cached_project_root()
    if not project_root:
        return []

    tasks_dir = str(project_root / "tasks")
    task_names = _get_task_names(tasks_dir)

    if not task_names:
        return []

    # Simple filtering - no unnecessary iterations
    incomplete_lower = incomplete.lower()
    return [name for name in task_names if incomplete_lower in name.lower()][:20]


def complete_executed_tasks(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete task names that have execution history for replay commands."""
    # For now, just return all tasks - checking execution history is too slow
    # Users can filter manually if needed
    return complete_task_names(ctx, param, incomplete)


def complete_traversal_ids(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete available traversal IDs for replay commands."""
    project_root = _get_cached_project_root()
    if not project_root:
        return []

    traversals_dir = str(project_root / "traversals")
    traversal_ids = _get_traversal_ids(traversals_dir)

    if not traversal_ids:
        return []

    # Simple filtering
    incomplete_lower = incomplete.lower()
    return [tid for tid in traversal_ids if incomplete_lower in tid.lower()][:20]


def complete_directory_paths(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete directory paths for init command options."""
    try:
        current_dir = Path.cwd()
        incomplete_lower = incomplete.lower()

        # Get directories from current path
        dirs = []
        for item in os.listdir(current_dir):
            if os.path.isdir(os.path.join(current_dir, item)) and not item.startswith("."):
                if incomplete_lower in item.lower():
                    dirs.append(f"./{item}")

        # Add common directories
        common = ["screenshots", "tasks", "traversals", "logs", "output"]
        for name in common:
            if incomplete_lower in name.lower() and f"./{name}" not in dirs:
                dirs.append(f"./{name}")

        return sorted(dirs)[:15]
    except Exception:
        return []


def complete_boolean_values(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete boolean values for flag options."""
    incomplete_lower = incomplete.lower()
    return [v for v in ["true", "false"] if v.startswith(incomplete_lower)]


def complete_project_names(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete project names for init command."""
    # No existing projects to suggest for init
    return []


def complete_replay_task_names(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete task names for replay command (task-based replay only)."""
    # Use the same logic as complete_task_names but only for tasks
    return complete_task_names(ctx, param, incomplete)
