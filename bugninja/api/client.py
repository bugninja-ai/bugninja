"""
Main client interface for Bugninja browser automation.

This module provides the `BugninjaClient` class, which serves as the **primary
entry point** for browser automation operations with a simple, intuitive API.

## Key Features

1. **BugninjaTask Execution** - Run browser automation tasks with `run_task()`
2. **Session Management** - Replay and heal recorded sessions
3. **Configuration** - Environment-aware configuration with validation
4. **Error Handling** - Comprehensive exception hierarchy
5. **Resource Management** - Automatic cleanup with context managers
"""

import asyncio
import time
from asyncio import Task as AsyncioTask
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from browser_use import (  # type: ignore[import-untyped]
    AgentHistoryList,
    BrowserSession,
)
from langchain_core.language_models.chat_models import BaseChatModel

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
from bugninja.api.models import (
    BugninjaConfig,
    BugninjaErrorType,
    BugninjaTask,
    BugninjaTaskError,
    BugninjaTaskResult,
    BulkBugninjaTaskResult,
    HealingStatus,
    OperationType,
    SessionInfo,
)
from bugninja.config import (
    ConfigurationFactory,
    create_llm_model_from_config,
    create_provider_model_from_settings,
)
from bugninja.config.llm_config import LLMConfig
from bugninja.events import EventPublisherManager
from bugninja.replication import ReplicatorRun
from bugninja.schemas.pipeline import Traversal
from bugninja.utils.logging_config import logger
from bugninja.utils.prompt_string_factories import AUTHENTICATION_HANDLING_EXTRA_PROMPT


class ClientOperationType(Enum):
    """Enumeration of operation types for error handling."""

    TASK_EXECUTION = "task_execution"
    PARALLEL_TASK_EXECUTION = "parallel_task_execution"
    SESSION_REPLAY = "session_replay"
    PARALLEL_SESSION_REPLAY = "parallel_session_replay"
    LIST_SESSIONS = "list_sessions"
    CLEANUP = "cleanup"


class BugninjaClient:
    """Main entry point for Bugninja browser automation operations.

    This class provides a **simple, intuitive interface** for:
    - browser automation tasks
    - session replay with healing
    - parallel task execution
    - comprehensive error handling

    It also handles:
    - configuration management with environment variable support
    - event tracking and monitoring
    - resource cleanup and management
    - type-safe task and result models

    Attributes:
        config (BugninjaConfig): Configuration object for browser automation settings
        background (bool): Whether the client is running in background mode
        _settings: Internal configuration settings from ConfigurationFactory
        _event_manager (Optional[EventPublisherManager]): Event publisher manager for tracking operations
        _active_sessions (List[BrowserSession]): List of active browser sessions for cleanup

    ### Key Methods

    1. *async* **run_task()** -> `BugninjaTaskResult`: - Execute single browser automation task
    2. *async* **parallel_run_tasks()** -> `BulkBugninjaTaskResult`: - Execute multiple tasks in parallel
    3. *async* **replay_session()** -> `BugninjaTaskResult`: - Replay recorded session with healing
    4. *async* **parallel_replay_sessions()** -> `BulkBugninjaTaskResult`: - Replay multiple sessions in parallel
    5. *async* **parallel_run_mixed()** -> `BulkBugninjaTaskResult`: - Execute mixed traversals and tasks concurrently
    6. **list_sessions()** -> `List[SessionInfo]`: - List available session files
    7. *async* **cleanup()** -> `None`: - Clean up all resources

    Example:
        ```python
        from bugninja.api.client import BugninjaClient
        from bugninja.api.models import BugninjaTask
        from pathlib import Path

        # Create client with default configuration
        client = BugninjaClient()

        # Execute a simple task
        task = BugninjaTask(
            description="Navigate to example.com and click login",
            max_steps=50,
            allowed_domains=["example.com"]
        )
        result = await client.run_task(task)

        if result.success:
            print(f"Task completed in {result.steps_completed} steps")
            print(f"Traversal saved to: {result.traversal_file}")
        else:
            print(f"Task failed: {result.error}")

        # Replay a recorded session from file
        session_file = Path("./traversals/session.json")
        replay_result = await client.replay_session(
            session_file,
            enable_healing=True
        )

        # Replay a recorded session from Traversal object
        traversal = Traversal(...)  # Some traversal object
        replay_result = await client.replay_session(
            traversal,
            enable_healing=True
        )

        # Execute mixed traversals and tasks concurrently
        executions = [
            Path("./traversals/session_1.json"),
            traversal,
            BugninjaTask(description="Check dashboard status")
        ]
        mixed_result = await client.parallel_run_mixed(
            executions,
            max_concurrent=3,
            enable_healing=True
        )

        # Clean up resources
        await client.cleanup()
        ```
    """

    def __init__(
        self,
        config: Optional[BugninjaConfig] = None,
        event_manager: Optional[EventPublisherManager] = None,
        background: bool = False,
        llm_config: Optional[LLMConfig] = None,
    ) -> None:
        """Initialize Bugninja client with optional configuration.

        Args:
            config (Optional[BugninjaConfig]): Optional configuration object. If not provided, uses
                   default configuration with environment variable support
            event_manager (Optional[EventPublisherManager]): Optional event publisher manager for tracking
            background (bool): Whether to run in background mode (disables console logging and enforces headless mode)
            llm_provider (Optional[LLMProvider]): Optional LLM provider to use (overrides config default)

        Raises:
            ConfigurationError: If configuration is invalid or initialization fails
        """
        try:
            # Use provided config or create default
            # BugninjaConfig validation happens automatically during instantiation
            self.config = config or BugninjaConfig()

            # Enforce headless mode when background=True
            if background:
                self.config.headless = True

            # Store background flag
            self.background = background

            # Store LLM configuration (use provided or create from settings)
            self._llm_config = llm_config

            # Initialize internal configuration
            self._settings = ConfigurationFactory.get_settings()

            # Store event manager
            self._event_manager = event_manager

            # Initialize session tracking
            self._active_sessions: List[BrowserSession] = []

        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Bugninja client: {e}", original_error=e)

    def _create_llm(self, temperature: Optional[float] = None) -> BaseChatModel:
        """Create LLM model using client configuration.

        Args:
            temperature (Optional[float]): Temperature setting (overrides config)

        Returns:
            BaseChatModel: Configured LLM model instance

        Raises:
            ValueError: If LLM configuration is invalid or missing
        """
        try:

            # Use provided LLM config or create from settings
            if self._llm_config is not None:

                config = self._llm_config
                if temperature is not None:
                    config.temperature = temperature
                return create_llm_model_from_config(config)
            else:
                return create_provider_model_from_settings(temperature)
        except Exception as e:
            raise ValueError(f"Failed to create LLM model: {e}")

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> BugninjaErrorType:
        """Classify errors using clean match-case structure.

        Args:
            error (Exception): The error to classify
            context (Dict[str, Any]): Context information for error classification

        Returns:
            BugninjaErrorType: The classified error type
        """
        # First check exception type
        error_type = type(error)

        if error_type == ValidationError:
            return BugninjaErrorType.VALIDATION_ERROR
        elif error_type == ConfigurationError:
            return BugninjaErrorType.CONFIGURATION_ERROR
        elif error_type == LLMError:
            return BugninjaErrorType.LLM_ERROR
        elif error_type == BrowserError:
            return BugninjaErrorType.BROWSER_ERROR
        elif error_type == TaskExecutionError:
            return BugninjaErrorType.TASK_EXECUTION_ERROR
        elif error_type == SessionReplayError:
            return BugninjaErrorType.SESSION_REPLAY_ERROR

        # Then check error message content
        error_message = str(error).lower()

        # Check for validation errors
        if any(
            keyword in error_message for keyword in ["validation", "invalid", "required", "missing"]
        ):
            return BugninjaErrorType.VALIDATION_ERROR
        # Check for LLM errors
        elif any(
            keyword in error_message
            for keyword in ["llm", "openai", "azure", "model", "token", "api"]
        ):
            return BugninjaErrorType.LLM_ERROR
        # Check for browser errors
        elif any(
            keyword in error_message
            for keyword in ["browser", "page", "element", "click", "navigate", "selector"]
        ):
            return BugninjaErrorType.BROWSER_ERROR
        # Check for task execution errors
        elif any(keyword in error_message for keyword in ["task", "execution", "step", "action"]):
            return BugninjaErrorType.TASK_EXECUTION_ERROR
        # Check for session replay errors
        elif any(
            keyword in error_message for keyword in ["session", "replay", "traversal", "json"]
        ):
            return BugninjaErrorType.SESSION_REPLAY_ERROR
        # Check for cleanup errors
        elif any(keyword in error_message for keyword in ["cleanup", "close", "resource"]):
            return BugninjaErrorType.CLEANUP_ERROR
        # Default to unknown error
        else:
            return BugninjaErrorType.UNKNOWN_ERROR

    def _get_suggested_action(self, error_type: BugninjaErrorType, context: Dict[str, Any]) -> str:
        """Get suggested action based on error type using match-case.

        Args:
            error_type (BugninjaErrorType): The classified error type
            context (Dict[str, Any]): Context information for the error

        Returns:
            str: Suggested action to resolve the error
        """
        match error_type:
            case BugninjaErrorType.VALIDATION_ERROR:
                return "Check input parameters and ensure all required fields are provided"
            case BugninjaErrorType.CONFIGURATION_ERROR:
                return "Verify configuration settings and environment variables"
            case BugninjaErrorType.LLM_ERROR:
                return "Check LLM provider credentials and API configuration"
            case BugninjaErrorType.BROWSER_ERROR:
                return "Verify browser installation and check for element selectors"
            case BugninjaErrorType.TASK_EXECUTION_ERROR:
                return "Review task description and check for invalid actions"
            case BugninjaErrorType.SESSION_REPLAY_ERROR:
                return "Verify session file format and check for corrupted data"
            case BugninjaErrorType.CLEANUP_ERROR:
                return "Check system resources and browser session state"
            case BugninjaErrorType.UNKNOWN_ERROR:
                return "Review logs for detailed error information"

    def _create_bulk_error_result(
        self, error: Exception, task_list: List[BugninjaTask], execution_time: float
    ) -> BulkBugninjaTaskResult:
        """Create bulk error result for parallel task execution failures.

        Args:
            error (Exception): The error that caused the bulk operation to fail
            task_list (List[BugninjaTask]): List of tasks that were being executed
            execution_time (float): Time spent before the error occurred

        Returns:
            BulkBugninjaTaskResult: Bulk result indicating complete failure
        """
        error_type = self._classify_error(error, {"operation": "parallel_execution"})
        suggested_action = self._get_suggested_action(error_type, {})

        return BulkBugninjaTaskResult(
            overall_success=False,
            total_tasks=len(task_list),
            successful_tasks=0,
            failed_tasks=len(task_list),
            total_execution_time=execution_time,
            individual_results=[],
            error_summary={error_type: len(task_list)},
            metadata={
                "error_type": error_type.value,
                "error_message": str(error),
                "suggested_action": suggested_action,
                "operation": "parallel_execution",
            },
        )

    def _create_error_result(
        self,
        error: Exception,
        operation_type: OperationType,
        context: Dict[str, Any],
        execution_time: float,
    ) -> BugninjaTaskResult:
        """Create comprehensive error result with proper error classification.

        Args:
            error (Exception): The error that occurred
            operation_type (OperationType): Type of operation that failed
            context (Dict[str, Any]): Context information for the error
            execution_time (float): Time spent before the error occurred

        Returns:
            BugninjaTaskResult: Comprehensive error result with classification and suggestions
        """
        error_type = self._classify_error(error, context)
        suggested_action = self._get_suggested_action(error_type, context)

        return BugninjaTaskResult(
            success=False,
            operation_type=operation_type,
            healing_status=HealingStatus.NONE,
            execution_time=execution_time,
            steps_completed=context.get("steps_completed", 0),
            total_steps=context.get("total_steps", 0),
            traversal=None,
            traversal_file=context.get("traversal_file"),
            screenshots_dir=context.get("screenshots_dir"),
            error=BugninjaTaskError(
                error_type=error_type,
                message=str(error),
                details=context,
                original_error=f"{type(error).__name__}: {str(error)}",
                suggested_action=suggested_action,
            ),
            metadata={
                "error_context": context,
                "operation_type": operation_type.value,
                "error_classification": error_type.value,
            },
        )

    def _create_error_summary(
        self, results: List[BugninjaTaskResult]
    ) -> Dict[BugninjaErrorType, int]:
        """Create error summary from individual task results.

        Args:
            results (List[BugninjaTaskResult]): List of individual task results

        Returns:
            Dict[BugninjaErrorType, int]: Summary of error types and their counts
        """
        error_counts: Dict[BugninjaErrorType, int] = {}

        for result in results:
            if not result.success and result.error:
                error_type = result.error.error_type
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return error_counts

    def _handle_execution_error(
        self,
        error: Exception,
        operation_type: ClientOperationType,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Centralized error handling for all execution operations.

        This method classifies errors and raises appropriate exceptions with
        proper context and details for debugging.

        Args:
            error (Exception): The original exception that occurred
            operation_type (ClientOperationType): Type of operation that failed
            context (Optional[Dict[str, Any]]): Optional context information for the error

        Raises:
            LLMError: If the error is related to LLM operations
            BrowserError: If the error is related to browser operations
            ValidationError: If the error is a validation issue
            TaskExecutionError: For general task execution failures
            SessionReplayError: For session replay failures
        """
        # Re-raise known exception types
        if isinstance(
            error, (LLMError, BrowserError, ValidationError, TaskExecutionError, SessionReplayError)
        ):
            raise

        # Classify error based on content and context
        error_message = str(error).lower()

        # LLM-related errors
        if any(
            keyword in error_message
            for keyword in ["llm", "openai", "azure", "model", "token", "api"]
        ):
            raise LLMError(
                f"LLM operation failed during {operation_type.value}: {error}",
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                original_error=error,
            )

        # Browser-related errors
        if any(
            keyword in error_message
            for keyword in ["browser", "page", "element", "click", "navigate", "selector"]
        ):
            raise BrowserError(
                f"Browser operation failed during {operation_type.value}: {error}",
                browser_action=operation_type.value,
                original_error=error,
            )

        # Validation errors
        if any(
            keyword in error_message for keyword in ["validation", "invalid", "required", "missing"]
        ):
            raise ValidationError(
                f"Validation error during {operation_type.value}: {error}",
                field_name=context.get("field_name") if context else None,
                field_value=context.get("field_value") if context else None,
            )

        # Use match statement for operation-specific error handling
        match operation_type:
            case ClientOperationType.TASK_EXECUTION | ClientOperationType.PARALLEL_TASK_EXECUTION:
                raise TaskExecutionError(
                    f"BugninjaTask execution failed: {error}",
                    task_description=(
                        context.get("task_description", "Unknown task")
                        if context
                        else "Unknown task"
                    ),
                    steps_completed=context.get("steps_completed", 0) if context else 0,
                    original_error=error,
                )
            case ClientOperationType.SESSION_REPLAY:
                raise SessionReplayError(
                    f"Session {operation_type.value} failed: {error}",
                    session_file=context.get("session_file") if context else None,
                    original_error=error,
                )
            case ClientOperationType.LIST_SESSIONS | ClientOperationType.CLEANUP:
                # Generic error for utility operations
                raise BugninjaError(
                    f"Operation '{operation_type.value}' failed: {error}",
                    original_error=error,
                )
            case _:
                # Fallback for any unhandled operation types
                raise BugninjaError(
                    f"Operation '{operation_type.value}' failed: {error}",
                    original_error=error,
                )

    async def _ensure_cleanup(
        self,
        agent: Optional[Any] = None,
        browser_session: Optional[BrowserSession] = None,
        replicator: Optional[Any] = None,
    ) -> None:
        """Ensure consistent cleanup for all agent types and resources.

        This method provides centralized cleanup logic that handles different
        types of agents and resources gracefully, preventing resource leaks
        and ensuring proper cleanup regardless of success or failure.

        Args:
            agent (Optional[Any]): NavigatorAgent, HealerAgent, or other agent instance to cleanup
            browser_session (Optional[BrowserSession]): BrowserSession instance to cleanup
            replicator (Optional[Any]): ReplicatorRun instance to cleanup
        """
        try:
            # Cleanup replicator if provided
            if replicator:
                try:
                    await replicator.cleanup()
                except Exception as e:
                    # Log cleanup error but don't raise to avoid masking original errors
                    logger.warning(f"Replicator cleanup failed: {e}")

            # Cleanup agent if provided
            if agent:
                try:
                    if hasattr(agent, "close"):
                        await agent.close()
                    elif hasattr(agent, "cleanup"):
                        await agent.cleanup()
                except Exception as e:
                    # Log cleanup error but don't raise to avoid masking original errors
                    logger.warning(f"Agent cleanup failed: {e}")

            # Cleanup browser session if provided
            if browser_session:
                try:
                    if browser_session in self._active_sessions:
                        await browser_session.close()
                        self._active_sessions.remove(browser_session)
                except Exception as e:
                    # Log cleanup error but don't raise to avoid masking original errors
                    logger.warning(f"Browser session cleanup failed: {e}")

        except Exception as e:
            # Log any unexpected cleanup errors but don't raise
            logger.warning(f"Unexpected cleanup error: {e}")

    async def run_task(self, task: BugninjaTask) -> BugninjaTaskResult:
        """Execute a browser automation task.

        This method creates a `NavigatorAgent` and executes the specified task,
        recording the session and providing detailed results.

        Args:
            task (BugninjaTask): The task to execute, containing description and parameters

        Returns:
            BugninjaTaskResult: Result containing execution status and traversal data

        Raises:
            TaskExecutionError: If task execution fails
            ConfigurationError: If configuration is invalid
            LLMError: If LLM operations fail
            BrowserError: If browser operations fail
            ValidationError: If task validation fails

        Example:
            ```python
            task = BugninjaTask(
                description="Navigate to example.com and click the login button",
                max_steps=50,
                allowed_domains=["example.com"],
                secrets={"username": "user@example.com", "password": "secret"}
            )
            result = await client.run_task(task)

            if result.success:
                print(f"Task completed in {result.steps_completed} steps")
                print(f"Session saved to: {result.traversal_file}")
            else:
                print(f"Task failed: {result.error}")
            ```
        """
        start_time = time.time()
        browser_session = None
        agent: Optional[NavigatorAgent] = None

        try:
            # Validate task description
            if not task.description.strip():
                raise ValidationError(
                    "BugninjaTask description cannot be empty", field_name="description"
                )

            browser_session = self.config.build_bugninja_session_from_config_for_run(task.run_id)
            # TODO! this is extremely ugly and a strong antipattern, but it works for now, has to get rid of it later
            browser_session.browser_profile.allowed_domains = task.allowed_domains
            self._active_sessions.append(browser_session)

            # Create LLM with configured temperature
            llm = self._create_llm(temperature=self.config.llm_temperature)

            # Create and run agent with task parameters
            agent = NavigatorAgent(
                run_id=task.run_id,
                task=task.description,
                llm=llm,
                browser_session=browser_session,
                sensitive_data=task.secrets,
                extend_planner_system_message=AUTHENTICATION_HANDLING_EXTRA_PROMPT,
                video_recording_config=self.config.video_recording,
            )

            # Set event manager if available
            if self._event_manager:
                agent.event_manager = self._event_manager

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

            return BugninjaTaskResult(
                success=True,
                operation_type=OperationType.FIRST_TRAVERSAL,
                healing_status=HealingStatus.NONE,  # Navigation doesn't use healing
                execution_time=execution_time,
                steps_completed=(
                    len(history.history) if history and hasattr(history, "history") else 0
                ),
                total_steps=task.max_steps or self.config.default_max_steps,
                traversal=agent._traversal if hasattr(agent, "_traversal") else None,
                traversal_file=traversal_file,
                screenshots_dir=screenshots_dir,
                metadata={
                    "task_description": task.description,
                    "enable_healing": task.enable_healing,
                    "browser_headless": self.config.headless,
                    "allowed_domains": task.allowed_domains,
                    "has_secrets": task.secrets is not None,
                },
                error=None,  # No error if success
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context = {
                "task_description": task.description,
                "steps_completed": 0,
                "total_steps": task.max_steps or self.config.default_max_steps,
                "browser_headless": self.config.headless,
                "allowed_domains": task.allowed_domains,
                "has_secrets": task.secrets is not None,
            }
            return self._create_error_result(
                e, OperationType.FIRST_TRAVERSAL, context, execution_time
            )

        finally:
            if agent:
                # Ensure consistent cleanup for both success and failure
                await self._ensure_cleanup(agent=agent, browser_session=browser_session)

    async def parallel_run_tasks(self, task_list: List[BugninjaTask]) -> BulkBugninjaTaskResult:
        """Execute multiple browser automation tasks in parallel.

        This method creates multiple `NavigatorAgent` instances and executes
        them concurrently, providing aggregate results and error summaries.

        Args:
            task_list (List[BugninjaTask]): List of tasks to execute in parallel

        Returns:
            BulkBugninjaTaskResult: Aggregate result containing individual task results and summaries

        Raises:
            ValidationError: If any task validation fails
            TaskExecutionError: If bulk task execution fails

        Example:
            ```python
            tasks = [
                BugninjaTask(description="Task 1: Login to app"),
                BugninjaTask(description="Task 2: Navigate to dashboard"),
                BugninjaTask(description="Task 3: Check notifications")
            ]

            result = await client.parallel_run_tasks(tasks)

            if result.overall_success:
                print(f"All {result.total_tasks} tasks completed successfully")
            else:
                print(f"{result.failed_tasks} tasks failed out of {result.total_tasks}")
            ```
        """
        start_time = time.time()
        navigation_agents: List[NavigatorAgent] = []
        individual_results: List[BugninjaTaskResult] = []

        try:

            for task in task_list:
                # Validate task description
                if not task.description.strip():
                    raise ValidationError(
                        "BugninjaTask description cannot be empty", field_name="description"
                    )

                # Create browser session with configured settings (isolation handled in agent)
                browser_session = self.config.build_bugninja_session_from_config_for_run(
                    run_id=task.run_id
                )

                # TODO! this is extremely ugly and a strong antipattern, but it works for now, has to get rid of it later
                browser_session.browser_profile.allowed_domains = task.allowed_domains
                self._active_sessions.append(browser_session)

                # Create agent (isolation happens in _before_run_hook)
                agent = NavigatorAgent(
                    run_id=task.run_id,
                    task=task.description,
                    llm=self._create_llm(temperature=self.config.llm_temperature),
                    browser_session=browser_session,
                    sensitive_data=task.secrets,
                    extend_planner_system_message=AUTHENTICATION_HANDLING_EXTRA_PROMPT,
                    video_recording_config=self.config.video_recording,
                )

                # Set event manager if available
                if self._event_manager:
                    agent.event_manager = self._event_manager

                navigation_agents.append(agent)

            async with asyncio.TaskGroup() as tg:
                navigation_runs: List[AsyncioTask[Optional[AgentHistoryList]]] = []
                for nav_agent in navigation_agents:
                    navigation_runs.append(tg.create_task(nav_agent.run()))

            # Execute tasks in parallel and collect results
            for background_task in navigation_runs:
                try:
                    history = background_task.result()
                    # Create individual result for successful task
                    individual_result = BugninjaTaskResult(
                        success=True,
                        operation_type=OperationType.FIRST_TRAVERSAL,
                        healing_status=HealingStatus.NONE,
                        execution_time=0.0,  # Individual time not tracked in bulk
                        steps_completed=(
                            len(history.history) if history and hasattr(history, "history") else 0
                        ),
                        total_steps=0,  # Would need to track from original task
                        traversal=None,  # Would need to extract from agent
                        traversal_file=None,
                        screenshots_dir=None,
                        metadata={
                            "operation": "parallel_execution",
                            "task_index": len(individual_results),
                        },
                    )
                    individual_results.append(individual_result)
                except Exception as e:
                    # Create individual result for failed task
                    individual_result = self._create_error_result(
                        e,
                        OperationType.FIRST_TRAVERSAL,
                        {"task_index": len(individual_results), "operation": "parallel_execution"},
                        0.0,
                    )
                    individual_results.append(individual_result)

            # Calculate aggregate metrics
            total_execution_time = time.time() - start_time
            successful_tasks = sum(1 for r in individual_results if r.success)
            failed_tasks = len(individual_results) - successful_tasks
            error_summary = self._create_error_summary(individual_results)

            return BulkBugninjaTaskResult(
                overall_success=all(r.success for r in individual_results),
                total_tasks=len(task_list),
                successful_tasks=successful_tasks,
                failed_tasks=failed_tasks,
                total_execution_time=total_execution_time,
                individual_results=individual_results,
                error_summary=error_summary,
                metadata={
                    "operation": "parallel_execution",
                    "total_tasks": len(task_list),
                    "successful_tasks": successful_tasks,
                    "failed_tasks": failed_tasks,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return self._create_bulk_error_result(e, task_list, execution_time)

        finally:
            # Ensure consistent cleanup for all navigation agents
            for agent in navigation_agents:
                await self._ensure_cleanup(agent=agent)

            await self.cleanup()

    async def replay_session(
        self,
        session: Union[Path, Traversal],
        pause_after_each_step: bool = False,
        enable_healing: bool = True,
    ) -> BugninjaTaskResult:
        """Replay a recorded browser session.

        This method replays a previously recorded browser session using
        the `ReplicatorRun` functionality with optional healing capabilities.

        Args:
            session (Union[Path, Traversal]): Path to the session file or a Traversal object to replay
            pause_after_each_step (bool): Whether to pause and wait for Enter key after each step.
                                          Defaults to False for automated replay
            enable_healing (bool): Whether to enable healing when actions fail (default: True)

        Returns:
            BugninjaTaskResult: Result containing replay status and traversal data

        Raises:
            SessionReplayError: If session replay fails
            ValidationError: If session file is invalid or doesn't exist

        Example:
            ```python
            # Replay from file path
            session_file = Path("./traversals/session_20240115.json")
            result = await client.replay_session(session_file)

            # Replay from Traversal object
            traversal = Traversal(...)  # Some traversal object
            result = await client.replay_session(traversal)

            # Interactive replay with pauses and healing
            result = await client.replay_session(session_file, pause_after_each_step=True)

            # Replay without healing (fails immediately on errors)
            result = await client.replay_session(session_file, enable_healing=False)

            if result.success:
                print("Session replayed successfully")
            else:
                print(f"Session replay failed: {result.error}")
            ```
        """
        start_time = time.time()

        # Validate session input
        if isinstance(session, Path):
            if not session.exists():
                raise ValidationError(
                    f"Session file does not exist: {session}",
                    field_name="session",
                    field_value=str(session),
                )

            # Validate session file is JSON
            if not session.suffix == ".json":
                raise ValidationError(
                    f"Session file must be a JSON file: {session}",
                    field_name="session",
                    field_value=str(session),
                )
        elif not isinstance(session, Traversal):
            raise ValidationError(
                f"Invalid session type: {type(session)}. Expected Path or Traversal.",
                field_name="session",
                field_value=str(session),
            )

        try:

            # Create replicator with configured settings
            # Convert Path to string for ReplicatorRun
            traversal_source = str(session) if isinstance(session, Path) else session
            replicator = ReplicatorRun(
                traversal_source=traversal_source,
                pause_after_each_step=pause_after_each_step,
                sleep_after_actions=1.0,  # Default sleep time
                enable_healing=enable_healing,
                healing_llm_config=self._llm_config,  # Pass client's LLM config
            )

            # Execute replay and capture result
            try:
                await replicator.start()
                success = True
                error = None
            except Exception as e:
                success = False
                error = e

            finally:
                # Ensure consistent cleanup for both success and failure
                await self._ensure_cleanup(replicator=replicator)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Determine healing status
            healing_status = (
                HealingStatus.USED if replicator.healing_happened else HealingStatus.NONE
            )

            # Create proper error object if there was an error
            error_obj = None
            if not success and error:
                context = {
                    "session": str(session) if isinstance(session, Path) else "traversal_object",
                    "pause_after_each_step": pause_after_each_step,
                    "enable_healing": enable_healing,
                }
                error_type = self._classify_error(error, context)
                suggested_action = self._get_suggested_action(error_type, context)
                error_obj = BugninjaTaskError(
                    error_type=error_type,
                    message=str(error),
                    details=context,
                    original_error=f"{type(error).__name__}: {str(error)}",
                    suggested_action=suggested_action,
                )

            # Determine traversal file and screenshots directory
            if isinstance(session, Path):
                traversal_file = session
                screenshots_dir = self.config.screenshots_dir / session.stem
            else:
                # For Traversal objects, we don't have a file path
                traversal_file = None
                screenshots_dir = self.config.screenshots_dir / f"traversal_{replicator.run_id}"

            return BugninjaTaskResult(
                success=success,
                operation_type=OperationType.REPLAY,
                healing_status=healing_status,
                execution_time=execution_time,
                steps_completed=getattr(replicator, "actions_completed", 0),
                total_steps=getattr(replicator, "total_actions", 0),
                traversal=replicator._traversal if hasattr(replicator, "_traversal") else None,
                traversal_file=traversal_file,
                screenshots_dir=screenshots_dir,
                error=error_obj,
                metadata={
                    "replay_type": "session_replay",
                    "session": str(session) if isinstance(session, Path) else "traversal_object",
                    "pause_after_each_step": pause_after_each_step,
                    "healing_enabled": enable_healing,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            context = {
                "session": str(session) if isinstance(session, Path) else "traversal_object",
                "pause_after_each_step": pause_after_each_step,
                "enable_healing": enable_healing,
                "file_exists": isinstance(session, Path) and session.exists(),
                "file_size": (
                    isinstance(session, Path) and session.stat().st_size
                    if isinstance(session, Path) and session.exists()
                    else 0
                ),
            }
            return self._create_error_result(e, OperationType.REPLAY, context, execution_time)

    async def parallel_replay_sessions(
        self,
        sessions: List[Union[Path, Traversal]],
        pause_after_each_step: bool = False,
        enable_healing: bool = True,
    ) -> BulkBugninjaTaskResult:
        """Replay multiple recorded browser sessions in parallel.

        This method replays multiple previously recorded browser sessions
        concurrently using the `ReplicatorRun` functionality.

        Args:
            sessions (List[Union[Path, Traversal]]): List of paths to session files or Traversal objects to replay
            pause_after_each_step (bool): Whether to pause and wait for Enter key after each step.
                                          Defaults to False for automated replay
            enable_healing (bool): Whether to enable healing when actions fail (default: True)

        Returns:
            BulkBugninjaTaskResult: Result containing replay status and metrics for all sessions

        Raises:
            ValidationError: If any session file is invalid
            SessionReplayError: If bulk session replay fails

        Example:
            ```python
            # Replay multiple files
            session_files = [
                Path("./traversals/session_1.json"),
                Path("./traversals/session_2.json"),
                Path("./traversals/session_3.json")
            ]

            # Replay mixed list of files and Traversal objects
            sessions = [
                Path("./traversals/session_1.json"),
                traversal_object_1,
                Path("./traversals/session_2.json"),
                traversal_object_2
            ]

            # Automated parallel replay with healing (default)
            result = await client.parallel_replay_sessions(sessions)

            # Interactive parallel replay with pauses and healing
            result = await client.parallel_replay_sessions(
                sessions,
                pause_after_each_step=True
            )

            # Parallel replay without healing
            result = await client.parallel_replay_sessions(
                sessions,
                enable_healing=False
            )

            if result.overall_success:
                print(f"All {result.total_tasks} sessions replayed successfully")
            else:
                print(f"{result.failed_tasks} sessions failed out of {result.total_tasks}")
            ```
        """
        start_time = time.time()
        replicators: List[ReplicatorRun] = []
        individual_results: List[BugninjaTaskResult] = []

        try:
            # Validate all sessions
            for session in sessions:
                if isinstance(session, Path):
                    if not session.exists():
                        raise ValidationError(
                            f"Session file does not exist: {session}",
                            field_name="session",
                            field_value=str(session),
                        )

                    if not session.suffix == ".json":
                        raise ValidationError(
                            f"Session file must be a JSON file: {session}",
                            field_name="session",
                            field_value=str(session),
                        )
                elif not isinstance(session, Traversal):
                    raise ValidationError(
                        f"Invalid session type: {type(session)}. Expected Path or Traversal.",
                        field_name="session",
                        field_value=str(session),
                    )

            # Create replicators for all sessions
            for session in sessions:
                # Convert Path to string for ReplicatorRun
                traversal_source = str(session) if isinstance(session, Path) else session
                replicator = ReplicatorRun(
                    traversal_source=traversal_source,
                    pause_after_each_step=pause_after_each_step,
                    sleep_after_actions=1.0,  # Default sleep time
                    enable_healing=enable_healing,
                    healing_llm_config=self._llm_config,  # Pass client's LLM config
                )
                replicators.append(replicator)

            # Execute all sessions in parallel
            async with asyncio.TaskGroup() as tg:
                replay_tasks: List[AsyncioTask[None]] = []
                for replicator in replicators:
                    replay_tasks.append(tg.create_task(replicator.start()))

            # Process results from parallel execution
            for i, background_task in enumerate(replay_tasks):
                try:
                    # Wait for task completion
                    background_task.result()

                    # Get the corresponding replicator and session
                    replicator = replicators[i]
                    session = sessions[i]

                    # Determine traversal file and screenshots directory
                    if isinstance(session, Path):
                        traversal_file = session
                        screenshots_dir = self.config.screenshots_dir / session.stem
                    else:
                        # For Traversal objects, we don't have a file path
                        traversal_file = None
                        screenshots_dir = (
                            self.config.screenshots_dir / f"traversal_{replicator.run_id}"
                        )

                    # Create individual result for successful session
                    individual_result = BugninjaTaskResult(
                        success=True,
                        operation_type=OperationType.REPLAY,
                        healing_status=(
                            HealingStatus.USED
                            if replicator.healing_happened
                            else HealingStatus.NONE
                        ),
                        execution_time=0.0,  # Individual time not tracked in bulk
                        steps_completed=getattr(replicator, "actions_completed", 0),
                        total_steps=getattr(replicator, "total_actions", 0),
                        traversal=(
                            replicator._traversal if hasattr(replicator, "_traversal") else None
                        ),
                        traversal_file=traversal_file,
                        screenshots_dir=screenshots_dir,
                        error=None,
                        metadata={
                            "operation": "parallel_replay",
                            "session_index": i,
                            "session": (
                                str(session) if isinstance(session, Path) else "traversal_object"
                            ),
                            "pause_after_each_step": pause_after_each_step,
                            "healing_enabled": enable_healing,
                        },
                    )
                    individual_results.append(individual_result)

                except Exception as e:
                    # Create individual result for failed session
                    session = sessions[i]
                    context = {
                        "session": (
                            str(session) if isinstance(session, Path) else "traversal_object"
                        ),
                        "pause_after_each_step": pause_after_each_step,
                        "enable_healing": enable_healing,
                        "session_index": i,
                        "operation": "parallel_replay",
                    }
                    individual_result = self._create_error_result(
                        e, OperationType.REPLAY, context, 0.0
                    )
                    individual_results.append(individual_result)

            # Calculate aggregate metrics
            total_execution_time = time.time() - start_time
            successful_sessions = sum(1 for r in individual_results if r.success)
            failed_sessions = len(individual_results) - successful_sessions
            error_summary = self._create_error_summary(individual_results)

            return BulkBugninjaTaskResult(
                overall_success=all(r.success for r in individual_results),
                total_tasks=len(sessions),
                successful_tasks=successful_sessions,
                failed_tasks=failed_sessions,
                total_execution_time=total_execution_time,
                individual_results=individual_results,
                error_summary=error_summary,
                metadata={
                    "operation": "parallel_replay",
                    "total_sessions": len(sessions),
                    "successful_sessions": successful_sessions,
                    "failed_sessions": failed_sessions,
                    "pause_after_each_step": pause_after_each_step,
                    "healing_enabled": enable_healing,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return self._create_bulk_error_result(e, [], execution_time)

        finally:
            # Ensure consistent cleanup for all replicators
            for replicator in replicators:
                await self._ensure_cleanup(replicator=replicator)

    async def parallel_run_mixed(
        self,
        executions: List[Union[Path, Traversal, BugninjaTask]],
        max_concurrent: int = 5,
        pause_after_each_step: bool = False,
        enable_healing: bool = True,
    ) -> BulkBugninjaTaskResult:
        """Execute mixed traversal replays and tasks concurrently.

        This method executes a mixed list of traversal replays and browser automation tasks
        concurrently, with proper resource management and isolation.

        Args:
            executions (List[Union[Path, Traversal, BugninjaTask]]): Mixed list of file paths,
                   Traversal objects, or BugninjaTasks to execute
            max_concurrent (int): Maximum number of concurrent executions (default: 5)
            pause_after_each_step (bool): Whether to pause during replay (ignored for tasks)
            enable_healing (bool): Whether to enable healing for replays (ignored for tasks)

        Returns:
            BulkBugninjaTaskResult: Aggregate result containing individual execution results

        Raises:
            ValidationError: If any execution input is invalid
            TaskExecutionError: If bulk execution fails

        Example:
            ```python
            # Mixed execution with files, traversals, and tasks
            executions = [
                Path("./traversals/session_1.json"),
                traversal_object,
                BugninjaTask(description="Login to app"),
                Path("./traversals/session_2.json"),
                BugninjaTask(description="Check dashboard")
            ]

            result = await client.parallel_run_mixed(
                executions,
                max_concurrent=3,
                enable_healing=True
            )

            if result.overall_success:
                print(f"All {result.total_tasks} executions completed successfully")
            else:
                print(f"{result.failed_tasks} executions failed out of {result.total_tasks}")
            ```
        """
        start_time = time.time()
        individual_results: List[BugninjaTaskResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        try:
            # Validate all executions
            for i, execution in enumerate(executions):
                if isinstance(execution, Path):
                    if not execution.exists():
                        raise ValidationError(
                            f"Execution file does not exist: {execution}",
                            field_name="execution",
                            field_value=str(execution),
                        )
                    if not execution.suffix == ".json":
                        raise ValidationError(
                            f"Execution file must be a JSON file: {execution}",
                            field_name="execution",
                            field_value=str(execution),
                        )
                elif not isinstance(execution, (Traversal, BugninjaTask)):
                    raise ValidationError(
                        f"Invalid execution type at index {i}: {type(execution)}. "
                        "Expected Path, Traversal, or BugninjaTask.",
                        field_name="execution",
                        field_value=str(execution),
                    )

            # Create execution tasks
            async def execute_single(
                execution: Union[Path, Traversal, BugninjaTask], index: int
            ) -> BugninjaTaskResult:
                """Execute a single execution with proper resource management."""
                async with semaphore:
                    try:
                        if isinstance(execution, BugninjaTask):
                            # Execute as task
                            return await self.run_task(execution)
                        else:
                            # Execute as replay
                            return await self.replay_session(
                                execution,
                                pause_after_each_step=pause_after_each_step,
                                enable_healing=enable_healing,
                            )
                    except Exception as e:
                        # Create error result for failed execution
                        context = {
                            "execution_index": index,
                            "execution_type": type(execution).__name__,
                            "execution": (
                                str(execution) if isinstance(execution, Path) else "object"
                            ),
                        }
                        return self._create_error_result(
                            e, OperationType.FIRST_TRAVERSAL, context, 0.0
                        )

            # Execute all concurrently
            tasks = [execute_single(execution, i) for i, execution in enumerate(executions)]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle unexpected exceptions
                    context = {
                        "execution_index": i,
                        "execution_type": type(executions[i]).__name__,
                        "execution": (
                            str(executions[i]) if isinstance(executions[i], Path) else "object"
                        ),
                    }
                    individual_results.append(
                        self._create_error_result(
                            result, OperationType.FIRST_TRAVERSAL, context, 0.0
                        )
                    )
                elif isinstance(result, BugninjaTaskResult):
                    individual_results.append(result)
                else:
                    # Handle unexpected result types
                    context = {
                        "execution_index": i,
                        "execution_type": type(executions[i]).__name__,
                        "execution": (
                            str(executions[i]) if isinstance(executions[i], Path) else "object"
                        ),
                    }
                    individual_results.append(
                        self._create_error_result(
                            Exception(f"Unexpected result type: {type(result)}"),
                            OperationType.FIRST_TRAVERSAL,
                            context,
                            0.0,
                        )
                    )

            # Calculate aggregate metrics
            total_execution_time = time.time() - start_time
            successful_executions = sum(1 for r in individual_results if r.success)
            failed_executions = len(individual_results) - successful_executions
            error_summary = self._create_error_summary(individual_results)

            return BulkBugninjaTaskResult(
                overall_success=all(r.success for r in individual_results),
                total_tasks=len(executions),
                successful_tasks=successful_executions,
                failed_tasks=failed_executions,
                total_execution_time=total_execution_time,
                individual_results=individual_results,
                error_summary=error_summary,
                metadata={
                    "operation": "parallel_mixed",
                    "total_executions": len(executions),
                    "successful_executions": successful_executions,
                    "failed_executions": failed_executions,
                    "max_concurrent": max_concurrent,
                    "pause_after_each_step": pause_after_each_step,
                    "healing_enabled": enable_healing,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return self._create_bulk_error_result(e, [], execution_time)

    def list_sessions(self) -> List[SessionInfo]:
        """List all available session files.

        This method scans the configured traversals directory and returns
        metadata about all available session files for replay operations.

        Returns:
            List[SessionInfo]: List of session information objects containing metadata

        Example:
            ```python
            sessions = client.list_sessions()
            for session in sessions:
                print(f"Session: {session.file_path}")
                print(f"Created: {session.created_at}")
                print(f"Steps: {session.steps_count}")
            ```
        """
        sessions: List[SessionInfo] = []

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
                    success=True,  # Would need to parse file to determine success
                )

                sessions.append(session_info)

            except Exception:
                # Skip files that can't be processed
                continue

        # Sort by creation time (newest first)
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return sessions

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
            self._handle_execution_error(error=e, operation_type=ClientOperationType.CLEANUP)

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
