"""
Status command implementation for Bugninja CLI.

This module implements the 'status' command which shows the current
status of browser automation runs.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from bugninja.config import ConfigurationFactory, Environment
from bugninja.events import EventPublisherFactory, EventPublisherManager
from bugninja.events.types import EventPublisherType

console = Console()

app = typer.Typer(
    name="status",
    help="Monitor browser automation run status",
    add_completion=False,
    rich_markup_mode="rich",
)


# TODO!:AGENT have to rethink this whole section, because status querying only works if event tracking is enabled and there is
#! a valid event tracker added to the configuration


async def show_run_status(run_id: Optional[str] = None) -> None:
    """Show status of browser automation runs.

    Args:
        run_id: Optional specific run ID to show status for
    """
    settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)

    # Create event publishers with explicit configuration
    publisher_types = [EventPublisherType.REDIS]  # Default to Redis
    configs = {}

    # Add Redis configuration if available in settings
    if hasattr(settings, "redis_host") and settings.redis_host:
        configs["redis"] = {
            "redis_host": settings.redis_host,
            "redis_port": getattr(settings, "redis_port", 6379),
            "redis_db": getattr(settings, "redis_db", 0),
            "redis_password": getattr(settings, "redis_password", None),
        }

    publishers = EventPublisherFactory.create_publishers(publisher_types, configs)
    event_manager = EventPublisherManager(publishers)

    if not event_manager.has_publishers():
        console.print("❌ No event publishers available. Status monitoring is not available.")
        console.print("   Configure Redis connection in settings to enable monitoring.")
        console.print("   Example: Set redis_host, redis_port, etc. in your configuration")
        return

    # Show available publishers
    available_publishers = event_manager.get_available_publishers()
    console.print(f"✅ Available publishers: {len(available_publishers)}")
    for publisher in available_publishers:
        console.print(f"   - {publisher.__class__.__name__}")

    if run_id:
        # Show specific run status
        console.print(f"📊 Run Status: {run_id}")
        console.print("=" * 50)
        console.print("⚠️  Specific run status not yet implemented in new event system")
        console.print("   This feature will be available in future updates")

    else:
        # Show all runs summary
        console.print("📊 Browser Automation Runs Summary")
        console.print("=" * 50)
        console.print("⚠️  Run summary not yet implemented in new event system")
        console.print("   This feature will be available in future updates")
        console.print("   For now, check individual publisher status above")


@app.command()
def status(
    run_id: Optional[str] = typer.Option(
        None, "--run-id", "-r", help="Specific run ID to show status for"
    ),
) -> None:
    """Show status of browser automation runs.

    This command displays the current status of browser automation runs.
    If no run ID is provided, it shows a summary of all runs.
    """
    asyncio.run(show_run_status(run_id))


if __name__ == "__main__":
    app()
