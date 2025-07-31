#!/usr/bin/env python3
"""
Example usage of the Bugninja library with the new API structure.

This script demonstrates how to use the main public API of Bugninja
for browser automation tasks.
"""

import asyncio
from pathlib import Path

# Main package imports - simple and clean
from src import (
    BugninjaBrowserConfig,
    ConfigurationFactory,
    Environment,
    azure_openai_model,
)

# Submodule imports for advanced usage
from src.agents import BugninjaAgentBase
from src.schemas import BugninjaExtendedAction
from src.utils import ScreenshotManager


async def example_simple_usage():
    """Demonstrate simple usage of the main API."""
    print("=== Simple Usage Example ===")

    # Get configuration for different environments
    dev_settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)
    prod_settings = ConfigurationFactory.get_settings(Environment.PRODUCTION)

    print("✅ Configuration system working:")
    print(f"   - Development debug mode: {dev_settings.debug_mode}")
    print(f"   - Production debug mode: {prod_settings.debug_mode}")
    print(f"   - Development log level: {dev_settings.log_level}")
    print(f"   - Production log level: {prod_settings.log_level}")

    # Configure LLM with environment-specific settings
    llm = azure_openai_model(temperature=0.1, environment=Environment.DEVELOPMENT)

    # Configure browser using code-based settings
    browser_config = BugninjaBrowserConfig(
        viewport={
            "width": dev_settings.browser_config["viewport_width"],
            "height": dev_settings.browser_config["viewport_height"],
        },
        user_agent=dev_settings.browser_config["user_agent"],
    )

    print("✅ Configuration created successfully")
    print(f"   - LLM: {type(llm).__name__}")
    print(f"   - Browser Config: {browser_config.viewport}")
    print(f"   - Screenshots enabled: {dev_settings.screenshot_config['screenshots_dir']}")

    # Note: This would require actual browser session setup
    # agent = NavigatorAgent(
    #     task="Navigate to example.com and take a screenshot",
    #     llm=llm,
    #     browser_session=browser_session
    # )
    # await agent.run()


async def example_advanced_usage():
    """Demonstrate advanced usage with submodules."""
    print("\n=== Advanced Usage Example ===")

    # Get settings for configuration
    settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)

    # Custom agent development
    class CustomAgent(BugninjaAgentBase):
        async def _before_run_hook(self) -> None:
            print("🔄 Custom agent starting...")

        async def _before_step_hook(self, browser_state_summary, model_output) -> None:
            print("📝 Custom step processing...")

        async def _after_run_hook(self) -> None:
            print("✅ Custom agent finished!")

    print("✅ Custom agent class created")

    # Utility usage with code-based screenshot config
    screenshot_manager = ScreenshotManager(folder_prefix="example")
    print(f"✅ Screenshot manager created: {screenshot_manager.screenshots_dir}")

    # Data model usage
    extended_action = BugninjaExtendedAction(
        brain_state_id="test_id",
        action={"click": {"selector": "button"}},
        dom_element_data={"tag_name": "button"},
    )
    print(f"✅ Extended action created: {extended_action.brain_state_id}")

    # Configuration summary
    summary = ConfigurationFactory.get_settings_summary(Environment.DEVELOPMENT)
    print(f"✅ Configuration summary: {summary['environment']} environment")

    # Show code-based configurations
    print(f"   - Agent max steps: {settings.agent_config['max_steps']}")
    print(f"   - Replicator sleep time: {settings.replicator_config['sleep_after_actions']}")
    print(
        f"   - Authentication prompt length: {len(settings.authentication_handling_prompt)} chars"
    )


async def example_replication():
    """Demonstrate replication usage."""
    print("\n=== Replication Example ===")

    # Get settings for replication config
    settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)

    # Check if any traversal files exist
    traversal_files = list(Path("./traversals").glob("*.json"))

    if traversal_files:
        latest_file = max(traversal_files, key=lambda f: f.stat().st_mtime)
        print(f"📄 Found traversal file: {latest_file}")

        # Note: This would require actual browser session setup
        # replicator = ReplicatorRun(
        #     json_path=str(latest_file),
        #     pause_after_each_step=settings.replicator_config['pause_after_each_step']
        # )
        # await replicator.start()

        print("✅ Replicator configuration ready")
        print(f"   - Pause after each step: {settings.replicator_config['pause_after_each_step']}")
        print(f"   - Sleep after actions: {settings.replicator_config['sleep_after_actions']}")
    else:
        print("📄 No traversal files found in ./traversals/")


def example_import_patterns():
    """Demonstrate different import patterns."""
    print("\n=== Import Patterns ===")

    # Pattern 1: Main package imports (recommended for most users)
    print("Pattern 1 - Main package imports:")
    print("  from src import NavigatorAgent, ReplicatorRun, Traversal")

    # Pattern 2: Submodule imports (for advanced users)
    print("Pattern 2 - Submodule imports:")
    print("  from src.agents import HealerAgent, BugninjaAgentBase")
    print("  from src.schemas import StateComparison, ElementComparison")
    print("  from src.utils import ScreenshotManager, SelectorFactory")

    # Pattern 3: Direct imports (for specific needs)
    print("Pattern 3 - Direct imports:")
    print("  from src.agents.navigator_agent import NavigatorAgent")
    print("  from src.replication.replicator_run import ReplicatorRun")


async def main():
    """Run all examples."""
    print("🚀 Bugninja Library API Examples")
    print("=" * 50)

    await example_simple_usage()
    await example_advanced_usage()
    await example_replication()
    example_import_patterns()

    print("\n" + "=" * 50)
    print("✅ All examples completed successfully!")
    print("\nThe new API structure provides:")
    print("  • Clean, intuitive imports")
    print("  • Progressive disclosure of complexity")
    print("  • Backward compatibility")
    print("  • Clear separation of concerns")
    print("  • Code-based configuration for browser, agent, and replicator settings")


if __name__ == "__main__":
    asyncio.run(main())
