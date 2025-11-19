"""Platform command for Bugninja CLI.

This module provides the **platform command** for launching the Bugninja
web interface. It starts a local FastAPI server that serves both the API
and the React frontend.

## Key Features

1. **Local Web Server** - Runs FastAPI backend on localhost
2. **Auto Browser Opening** - Automatically opens browser to platform URL
3. **Project Context** - Operates on current Bugninja project
4. **Configuration Options** - Customizable port and host settings

## Usage Examples

```bash
# Start platform in current project
bugninja platform

# Start on custom port
bugninja platform --port 8080

# Allow network access
bugninja platform --host 0.0.0.0

# Don't auto-open browser
bugninja platform --no-browser
```
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

import rich_click as click
import uvicorn
from rich.console import Console
from rich.panel import Panel

from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.style import MARKDOWN_CONFIG

console = Console()


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to run the platform server on (default: 8000)",
)
@click.option(
    "--host",
    default="127.0.0.1",
    type=str,
    help="Host to bind the server to (default: 127.0.0.1, use 0.0.0.0 for network access)",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't automatically open browser",
)
@require_bugninja_project
def platform(port: int, host: str, no_browser: bool, project_root: Path) -> None:
    """Launch the Bugninja web platform interface.

    This command starts a **local web server** that provides a modern UI for
    managing and running your Bugninja tasks. The platform includes:

    - Task management and creation
    - Test execution and monitoring
    - Result visualization
    - Project settings configuration

    Args:
        port (int): Port number for the web server
        host (str): Host address to bind the server to
        no_browser (bool): Whether to skip automatic browser opening
        project_root (Path): Root directory of the Bugninja project

    Example:
        ```bash
        # Start platform with defaults
        bugninja platform

        # Start on custom port
        bugninja platform --port 8080

        # Allow network access (accessible from other devices)
        bugninja platform --host 0.0.0.0

        # Start without opening browser
        bugninja platform --no-browser
        ```

    Notes:
        - Requires a valid Bugninja project (use `bugninja init` to create one)
        - Platform operates on the current project directory
        - API documentation available at `/docs` endpoint
        - Press Ctrl+C to stop the server
    """
    # Display startup information
    platform_url = f"http://{host}:{port}"
    docs_url = f"{platform_url}/docs"

    console.print(
        Panel(
            f"🚀 Starting Bugninja Platform...\n\n"
            f"📂 Project: [cyan]{project_root}[/cyan]\n"
            f"🌐 Platform: [green]{platform_url}[/green]\n"
            f"📡 API Docs: [blue]{docs_url}[/blue]\n\n"
            f"[yellow]Press Ctrl+C to stop the server[/yellow]",
            title="[bold blue]Bugninja Platform[/bold blue]",
            border_style="blue",
        )
    )

    # Open browser automatically unless disabled
    if not no_browser:
        try:
            webbrowser.open(platform_url)
            console.print(f"[green]✓[/green] Browser opened to {platform_url}\n")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not open browser: {e}\n")

    # Import and create FastAPI app
    try:
        from bugninja_platform.backend.main import create_app

        app = create_app(project_root)

        # Run uvicorn server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Platform stopped by user[/yellow]")
    except Exception as e:
        console.print(
            Panel(
                f"[red]❌ Failed to start platform:[/red]\n\n{str(e)}",
                title="[bold red]Platform Error[/bold red]",
                border_style="red",
            )
        )
        raise click.Abort()
