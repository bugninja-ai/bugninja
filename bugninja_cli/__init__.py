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

## Architecture

The CLI is built using **Rich Click** for enhanced terminal output and follows a modular
architecture with utility modules for:
- Project validation and management
- Task execution and orchestration
- Configuration handling
- Styling and formatting
"""

import rich_click as click

from bugninja_cli.add import add
from bugninja_cli.init import init
from bugninja_cli.replay import replay
from bugninja_cli.run import run

# from bugninja_cli.stats import stats
from bugninja_cli.utils.style import MARKDOWN_CONFIG, display_logo


@click.group(invoke_without_command=True)
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.pass_context
def bugninja(ctx: click.Context) -> None:
    # Display logo for all invocations
    display_logo()

    # If no command is specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


bugninja.add_command(init)
bugninja.add_command(add)
bugninja.add_command(run)
bugninja.add_command(replay)
# TODO! later
# bugninja.add_command(stats)

if __name__ == "__main__":
    bugninja()
