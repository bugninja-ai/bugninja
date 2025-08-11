"""
Replay script for Bugninja browser automation sessions.

This script demonstrates how to use the Bugninja high-level API for
replaying recorded browser sessions with proper error handling.
"""

import asyncio
import glob
import os
from datetime import datetime
from pathlib import Path

from bugninja.api import BugninjaClient, BugninjaTaskResult


async def replay_latest_session() -> BugninjaTaskResult:
    """Replay the most recent recorded session.

    Returns:
        BugninjaTaskResult containing replay status and metadata
    """
    # Create client with default configuration
    client = BugninjaClient()

    try:
        # Find the most recent traversal file
        traversal_files = glob.glob("./traversals/*.json")

        if not traversal_files:
            raise FileNotFoundError("No traversal files found in ./traversals/ directory")

        latest_file = max(traversal_files, key=os.path.getctime)
        session_file = Path(latest_file)

        print(f"🔄 Replaying session: {session_file}")
        print(f"   File size: {session_file.stat().st_size} bytes")
        print(f"   Created: {datetime.fromtimestamp(session_file.stat().st_mtime)}")

        # Replay the session
        result = await client.replay_session(session_file=session_file, pause_after_each_step=True)

        if result.success:
            print("✅ Session replayed successfully!")
            print(f"   Execution time: {result.execution_time:.2f} seconds")
            print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            print(f"❌ Session replay failed: {result.error}")

        return result

    except Exception as e:
        print(f"❌ Session replay error: {e}")
        raise
    finally:
        await client.cleanup()


async def heal_latest_session() -> BugninjaTaskResult:
    """Heal the most recent recorded session.

    Returns:
        BugninjaTaskResult containing healing status and metadata
    """
    # Create client with default configuration
    client = BugninjaClient()

    try:
        # Find the most recent traversal file
        traversal_files = glob.glob("./traversals/*.json")

        if not traversal_files:
            raise FileNotFoundError("No traversal files found in ./traversals/ directory")

        latest_file = max(traversal_files, key=os.path.getctime)
        session_file = Path(latest_file)

        print(f"🩹 Healing session: {session_file}")
        print(f"   File size: {session_file.stat().st_size} bytes")
        print(f"   Created: {datetime.fromtimestamp(session_file.stat().st_mtime)}")

        # Heal the session
        result = await client.heal_session(session_file)

        if result.success:
            print("✅ Session healed successfully!")
            print(f"   Execution time: {result.execution_time:.2f} seconds")
            print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            print(f"❌ Session healing failed: {result.error}")

        return result

    except Exception as e:
        print(f"❌ Session healing error: {e}")
        raise
    finally:
        await client.cleanup()


async def list_available_sessions() -> None:
    """List all available sessions."""
    # Create client with default configuration
    client = BugninjaClient()

    try:
        sessions = client.list_sessions()

        if not sessions:
            print("📋 No sessions found. Run a task first to create sessions.")
            return

        print(f"📋 Found {len(sessions)} sessions:")
        print("-" * 60)

        for i, session in enumerate(sessions, 1):
            print(f"{i}. {session.file_path.name}")
            print(f"   Created: {session.created_at}")
            print(f"   Size: {session.file_path.stat().st_size} bytes")
            print(f"   Steps: {session.steps_count}")
            print()

    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
    finally:
        await client.cleanup()


async def main() -> None:
    """Main execution function."""
    print("🔄 Bugninja Session Replay")
    print("=" * 50)

    try:
        # List available sessions
        await list_available_sessions()

        print("\n🔄 Starting session replay...")

        # Replay the latest session
        result = await replay_latest_session()

        if result.success:
            print("\n✅ Session replay completed successfully!")
            print(f"   Traversal file: {result.traversal_file}")
            print(f"   Screenshots dir: {result.screenshots_dir}")
        else:
            print(f"\n❌ Session replay failed: {result.error}")

    except Exception as e:
        print(f"\n❌ Session replay failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
