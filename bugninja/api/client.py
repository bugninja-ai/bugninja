"""
Main client interface for Bugninja browser automation.

This module provides the BugninjaClient class, which serves as the primary
entry point for browser automation operations with a simple, intuitive API.

## Key Features

1. **Task Execution** - Run browser automation tasks with `run_task()`
2. **Session Management** - Replay and heal recorded sessions
3. **Configuration** - Environment-aware configuration with validation
4. **Error Handling** - Comprehensive exception hierarchy
5. **Resource Management** - Automatic cleanup with context managers
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from browser_use import BrowserProfile, BrowserSession  # type: ignore[import-untyped]

from bugninja.agents import NavigatorAgent
from bugninja.api.exceptions import (
    BrowserError,
    BugninjaError,
    ConfigurationError,
    LLMError,
    SessionReplayError,
    TaskExecutionError,
    ValidationError,
)
from bugninja.api.models import BugninjaConfig, SessionInfo, Task, TaskResult
from bugninja.config import ConfigurationFactory, Environment
from bugninja.models import azure_openai_model
from bugninja.replication import ReplicatorRun


class BugninjaClient:
    """Main entry point for Bugninja browser automation operations.

    This class provides a simple, intuitive interface for browser automation
    tasks, session replay, and healing operations. It handles configuration
    management, error handling, and provides comprehensive logging.

    ## Key Methods

    1. **run_task()** - Execute browser automation tasks
    2. **replay_session()** - Replay recorded sessions
    3. **heal_session()** - Heal failed sessions
    4. **list_sessions()** - List available sessions
    5. **cleanup()** - Clean up resources

    Example:
        ```python
        # Create client with default configuration
        client = BugninjaClient()

        # Execute a simple task
        task = Task(description="Navigate to example.com and click login")
        result = await client.run_task(task)

        if result.success:
            print(f"Task completed in {result.steps_completed} steps")
        else:
            print(f"Task failed: {result.error_message}")
        ```
    """

    def __init__(self, config: Optional[BugninjaConfig] = None) -> None:
        """Initialize Bugninja client with optional configuration.

        Args:
            config: Optional configuration object. If not provided, uses
                   default configuration with environment variable support.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        try:
            # Use provided config or create default
            self.config = config or BugninjaConfig()

            # Initialize internal configuration
            self._settings = ConfigurationFactory.get_settings(Environment.DEVELOPMENT)

            # Validate configuration
            self._validate_config()

            # Initialize session tracking
            self._active_sessions: List[BrowserSession] = []

        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Bugninja client: {e}", original_error=e)

    def _validate_config(self) -> None:
        """Validate client configuration.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        try:
            # Validate LLM configuration
            if not self.config.llm_provider:
                raise ValidationError("LLM provider is required", field_name="llm_provider")

            # Validate browser configuration
            if self.config.viewport_width < 800 or self.config.viewport_width > 3840:
                raise ValidationError(
                    "Viewport width must be between 800 and 3840",
                    field_name="viewport_width",
                    field_value=str(self.config.viewport_width),
                )

            if self.config.viewport_height < 600 or self.config.viewport_height > 2160:
                raise ValidationError(
                    "Viewport height must be between 600 and 2160",
                    field_name="viewport_height",
                    field_value=str(self.config.viewport_height),
                )

        except ValidationError:
            raise
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}", original_error=e)

    async def run_task(self, task: Task) -> TaskResult:
        """Execute a browser automation task.

        This method creates a NavigatorAgent and executes the specified task,
        recording the session and providing detailed results.

        Args:
            task: The task to execute, containing description and parameters.

        Returns:
            TaskResult containing execution status and session file path.

        Raises:
            TaskExecutionError: If task execution fails.
            ConfigurationError: If configuration is invalid.
            LLMError: If LLM operations fail.
            BrowserError: If browser operations fail.

        Example:
            ```python
            task = Task(
                description="Navigate to example.com and click the login button",
                target_url="https://example.com",
                max_steps=50,
                allowed_domains=["example.com"],
                secrets={"username": "user@example.com", "password": "secret"}
            )
            result = await client.run_task(task)

            if result.success:
                print(f"Task completed in {result.steps_completed} steps")
                print(f"Session saved to: {result.session_file}")
            else:
                print(f"Task failed: {result.error_message}")
            ```
        """
        start_time = time.time()
        browser_session = None

        try:
            # Validate task description
            if not task.description.strip():
                raise ValidationError("Task description cannot be empty", field_name="description")

            # Create browser session with configured settings
            browser_profile = BrowserProfile(
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                user_agent=self.config.user_agent,
                strict_selectors=self.config.strict_selectors,
                allowed_domains=task.allowed_domains,
            )

            browser_session = BrowserSession(browser_profile=browser_profile)
            await browser_session.start()
            self._active_sessions.append(browser_session)

            # Create LLM with configured temperature
            llm = azure_openai_model(
                temperature=self.config.llm_temperature, environment=Environment.DEVELOPMENT
            )

            # Create and run agent with task parameters
            agent = NavigatorAgent(
                task=task.description,
                llm=llm,
                browser_session=browser_session,
                sensitive_data=task.secrets,
                extend_planner_system_message=task.extend_planner_system_message,
            )

            # Execute task and record history
            history = await agent.run(max_steps=task.max_steps or self.config.default_max_steps)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Determine file paths from most recent files
            traversal_file = None
            screenshots_dir = None

            # Find the most recent traversal file
            traversal_files = list(self.config.traversals_dir.glob("*.json"))
            if traversal_files:
                traversal_file = max(traversal_files, key=lambda f: f.stat().st_mtime)

                # Create screenshots directory based on traversal file name
                if traversal_file:
                    screenshots_dir = self.config.screenshots_dir / traversal_file.stem

            return TaskResult(
                success=True,
                session_file=traversal_file,  # Use traversal file as session file
                error_message=None,
                steps_completed=(
                    len(history.history) if history and hasattr(history, "history") else 0
                ),
                execution_time=execution_time,
                traversal_file=traversal_file,
                screenshots_dir=screenshots_dir,
                metadata={
                    "task_description": task.description,
                    "target_url": str(task.target_url) if task.target_url else None,
                    "enable_healing": task.enable_healing,
                    "browser_headless": self.config.headless,
                    "allowed_domains": task.allowed_domains,
                    "has_secrets": task.secrets is not None,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time

            # Determine error type and create appropriate exception
            if isinstance(e, (LLMError, BrowserError, ValidationError)):
                raise

            if "LLM" in str(e) or "OpenAI" in str(e):
                raise LLMError(
                    f"LLM operation failed: {e}",
                    llm_provider=self.config.llm_provider,
                    llm_model=self.config.llm_model,
                    original_error=e,
                )

            if "browser" in str(e).lower() or "page" in str(e).lower():
                raise BrowserError(
                    f"Browser operation failed: {e}",
                    browser_action="task_execution",
                    original_error=e,
                )

            raise TaskExecutionError(
                f"Task execution failed: {e}",
                task_description=task.description,
                steps_completed=0,
                original_error=e,
            )

        finally:
            # Clean up browser session
            if browser_session and browser_session in self._active_sessions:
                # await browser_session.cleanup()
                self._active_sessions.remove(browser_session)

    async def replay_session(
        self, session_file: Path, pause_after_each_step: bool = False
    ) -> TaskResult:
        """Replay a recorded browser session.

        This method replays a previously recorded browser session using
        the ReplicatorRun functionality.

        Args:
            session_file: Path to the session file to replay.
            pause_after_each_step: Whether to pause and wait for Enter key after each step.
                                  Defaults to False for automated replay.

        Returns:
            TaskResult containing replay status and metadata.

        Raises:
            SessionReplayError: If session replay fails.
            ValidationError: If session file is invalid.

        Example:
            ```python
            session_file = Path("./traversals/session_20240115.json")

            # Automated replay (default)
            result = await client.replay_session(session_file)

            # Interactive replay with pauses
            result = await client.replay_session(session_file, pause_after_each_step=True)

            if result.success:
                print("Session replayed successfully")
            else:
                print(f"Session replay failed: {result.error_message}")
            ```
        """
        start_time = time.time()

        try:
            # Validate session file exists
            if not session_file.exists():
                raise ValidationError(
                    f"Session file does not exist: {session_file}",
                    field_name="session_file",
                    field_value=str(session_file),
                )

            # Validate session file is JSON
            if not session_file.suffix == ".json":
                raise ValidationError(
                    f"Session file must be a JSON file: {session_file}",
                    field_name="session_file",
                    field_value=str(session_file),
                )

            # Create replicator with configured settings
            replicator = ReplicatorRun(
                json_path=str(session_file),
                pause_after_each_step=pause_after_each_step,
                sleep_after_actions=1.0,  # Default sleep time
            )

            # Execute replay and capture result
            try:
                await replicator.start()
                success = True
                error_message = None
            except Exception as e:
                success = False
                error_message = str(e)

            # Calculate execution time
            execution_time = time.time() - start_time

            return TaskResult(
                success=success,
                session_file=session_file,
                error_message=error_message,
                execution_time=execution_time,
                traversal_file=session_file,
                screenshots_dir=self.config.screenshots_dir / session_file.stem,
                metadata={
                    "replay_type": "session_replay",
                    "session_file": str(session_file),
                    "pause_after_each_step": pause_after_each_step,
                },
            )

        except ValidationError:
            raise
        except Exception as e:
            execution_time = time.time() - start_time

            raise SessionReplayError(
                f"Session replay failed: {e}", session_file=str(session_file), original_error=e
            )

    async def heal_session(
        self, session_file: Path, pause_after_each_step: bool = False
    ) -> TaskResult:
        """Heal a failed browser session.

        This method attempts to heal a failed session by using the
        HealerAgent to recover from errors.

        Args:
            session_file: Path to the failed session file to heal.
            pause_after_each_step: Whether to pause and wait for Enter key after each step.
                                  Defaults to False for automated healing.

        Returns:
            TaskResult containing healing status and metadata.

        Raises:
            SessionReplayError: If session healing fails.
            ValidationError: If session file is invalid.

        Example:
            ```python
            failed_session = Path("./traversals/failed_session.json")

            # Automated healing (default)
            result = await client.heal_session(failed_session)

            # Interactive healing with pauses
            result = await client.heal_session(failed_session, pause_after_each_step=True)

            if result.success:
                print("Session healed successfully")
            else:
                print(f"Session healing failed: {result.error_message}")
            ```
        """
        start_time = time.time()

        try:
            # Validate session file exists
            if not session_file.exists():
                raise ValidationError(
                    f"Session file does not exist: {session_file}",
                    field_name="session_file",
                    field_value=str(session_file),
                )

            # Create replicator with healing enabled
            replicator = ReplicatorRun(
                json_path=str(session_file),
                pause_after_each_step=pause_after_each_step,
                sleep_after_actions=1.0,  # Default sleep time
            )

            # Execute replay with healing
            try:
                await replicator.start()
                success = True
                error_message = None
            except Exception as e:
                success = False
                error_message = str(e)

            # Calculate execution time
            execution_time = time.time() - start_time

            return TaskResult(
                success=success,
                session_file=session_file,
                error_message=error_message,
                execution_time=execution_time,
                traversal_file=session_file,
                screenshots_dir=self.config.screenshots_dir / session_file.stem,
                metadata={
                    "replay_type": "session_healing",
                    "session_file": str(session_file),
                    "healing_enabled": True,
                    "pause_after_each_step": pause_after_each_step,
                },
            )

        except ValidationError:
            raise
        except Exception as e:
            execution_time = time.time() - start_time

            raise SessionReplayError(
                f"Session healing failed: {e}", session_file=str(session_file), original_error=e
            )

    def list_sessions(self) -> List[SessionInfo]:
        """List all available session files.

        Returns:
            List of SessionInfo objects containing session metadata.

        Example:
            ```python
            sessions = client.list_sessions()
            for session in sessions:
                print(f"Session: {session.file_path}")
                print(f"Created: {session.created_at}")
                print(f"Steps: {session.steps_count}")
            ```
        """
        sessions = []

        try:
            # Find all session files in traversals directory
            session_files = list(self.config.traversals_dir.glob("*.json"))

            for file_path in session_files:
                try:
                    # Get file stats for metadata
                    stat = file_path.stat()

                    # Create session info with basic metadata
                    session_info = SessionInfo(
                        file_path=file_path,
                        created_at=datetime.fromtimestamp(stat.st_mtime),
                        steps_count=0,  # Would need to parse file to get actual count
                        target_url=None,  # Would need to parse file to get actual URL
                        success=True,  # Would need to parse file to determine success
                    )

                    sessions.append(session_info)

                except Exception:
                    # Skip files that can't be processed
                    continue

            # Sort by creation time (newest first)
            sessions.sort(key=lambda s: s.created_at, reverse=True)

            return sessions

        except Exception as e:
            raise BugninjaError(f"Failed to list sessions: {e}", original_error=e)

    async def cleanup(self) -> None:
        """Clean up client resources.

        This method should be called when the client is no longer needed
        to ensure proper cleanup of browser sessions and other resources.

        Example:
            ```python
            client = BugninjaClient()
            # ... use client ...
            await client.cleanup()
            ```
        """
        try:
            # Clean up active browser sessions
            for session in self._active_sessions:
                try:
                    await session.close()
                except Exception:
                    # Ignore cleanup errors
                    pass

            self._active_sessions.clear()

        except Exception as e:
            raise BugninjaError(f"Failed to cleanup client resources: {e}", original_error=e)

    def __enter__(self) -> "BugninjaClient":
        """Context manager entry."""
        return self

    async def __aenter__(self) -> "BugninjaClient":
        """Async context manager entry."""
        return self

    def __exit__(
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[object]
    ) -> None:
        """Context manager exit."""
        asyncio.create_task(self.cleanup())

    async def __aexit__(
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[object]
    ) -> None:
        """Async context manager exit."""
        await self.cleanup()
