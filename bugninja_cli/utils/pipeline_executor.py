"""
CLI BugninjaPipeline Executor for Bugninja CLI commands.

This module provides a CLI wrapper for BugninjaPipeline functionality, enabling
dependency management and execution using the unified BugninjaPipeline API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List

from rich.console import Console
from rich.panel import Panel

from bugninja_cli.utils.task_executor import TaskExecutor
from bugninja_cli.utils.task_manager import TaskManager

if TYPE_CHECKING:
    from bugninja.api.bugninja_pipeline import TaskRef, TaskSpec
    from bugninja.schemas.cli_schemas import (
        TaskExecutionResult,
        TaskInfo,
        TaskRunConfig,
    )


class PipelineExecutor:
    """CLI wrapper for BugninjaPipeline functionality.

    This class provides a bridge between CLI TaskInfo objects and the
    BugninjaPipeline API, handling dependency resolution and execution with
    rich console output.
    """

    def __init__(self, project_root: Path):
        """Initialize PipelineExecutor.

        Args:
            project_root: Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.console = Console()

    async def execute_with_dependencies(
        self, target_task: TaskInfo, task_manager: TaskManager
    ) -> TaskExecutionResult:
        """Execute task with all dependencies using BugninjaPipeline.

        Args:
            target_task: The target task to execute
            task_manager: Task manager instance

        Returns:
            TaskExecutionResult: Result of the execution
        """
        from bugninja.schemas.cli_schemas import TaskExecutionResult
        from bugninja.utils.logging_config import logger
        from bugninja_cli.utils.task_resolver import CLITaskResolver

        start_time = datetime.now()

        # Create CLI task resolver
        task_resolver = CLITaskResolver(task_manager)

        # Create pipeline from TOML dependencies (single source of truth)
        from bugninja.api.bugninja_pipeline import BugninjaPipeline

        pipeline = BugninjaPipeline.from_task_toml(
            target_task_identifier=target_task.folder_name, task_resolver=task_resolver
        )

        # Materialize TaskRef nodes to TaskSpec nodes
        try:
            materialized_pipeline = pipeline.materialize(task_resolver.resolve_task_ref)
        except Exception as e:
            self.console.print(
                Panel(
                    f"❌ Failed to resolve task dependencies: {str(e)}",
                    title="Task Resolution Error",
                    border_style="red",
                )
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskExecutionResult(
                success=False, execution_time=execution_time, result=None, error_message=str(e)
            )

        # Use BugninjaPipeline's built-in validation and execution
        try:
            # Note: Skipping upfront I/O validation for CLI mode as inputs are generated dynamically
            # materialized_pipeline.validate_io()

            # Show execution plan
            materialized_pipeline.print_plan()

            # Create client factory that generates task-specific clients
            from bugninja.api import BugninjaClient
            from bugninja.api.bugninja_pipeline import TaskRef
            from bugninja.schemas.cli_schemas import TaskExecutionResult
            from bugninja.schemas.models import BugninjaConfig

            # Get execution order directly from BugninjaPipeline
            task_order = materialized_pipeline.get_execution_order_folder_names()

            logger.info(f"🗂️ BugninjaPipeline execution order: {' → '.join(task_order)}")

            # Display dependency tree if there are multiple tasks
            if len(task_order) > 1:
                self._display_dependency_tree(target_task, task_order)

            # Track which task we're on
            task_counter = {"index": 0}

            def create_task_client(task_payload: TaskRef | TaskSpec) -> BugninjaClient:
                """Create a task-specific BugninjaClient with proper output directories.

                Enhanced to preserve data flow while maintaining directory isolation.
                Each task gets its own configuration loaded from its TOML file.
                """
                # TaskRef should never reach here due to materialization, but handle it for type safety
                if isinstance(task_payload, TaskRef):
                    raise ValueError("TaskRef should have been materialized before execution")

                # Load task-specific run configuration
                run_config = self._load_task_run_config(task_payload)
                config = BugninjaConfig(
                    headless=run_config.headless,
                    viewport_width=run_config.viewport_width,
                    viewport_height=run_config.viewport_height,
                    user_agent=run_config.user_agent,
                    enable_healing=run_config.enable_healing,
                    cli_mode=True,  # Enable CLI mode for proper directory structure
                )

                # Note: wait_between_actions, enable_vision, and enable_video_recording
                # are handled at the agent/browser level, not at the BugninjaConfig level

                # Get folder name from execution order
                idx = task_counter["index"]
                folder_name = task_order[idx] if idx < len(task_order) else target_task.folder_name

                # Enhanced logging for pipeline parameter passing debugging
                logger.info(
                    f"🏭 PipelineExecutor: Creating client for task {idx + 1}/{len(task_order)}: {folder_name}"
                )

                # Display current task execution status
                self._display_current_task_status(
                    folder_name, idx + 1, len(task_order), target_task
                )

                # Log I/O schema information for debugging parameter passing
                if hasattr(task_payload, "task") and task_payload.task.io_schema:
                    schema = task_payload.task.io_schema
                    if schema.input_schema:
                        input_keys = list(schema.input_schema.keys())
                        logger.info(f"📥 Task '{folder_name}' expects inputs: {input_keys}")
                    if schema.output_schema:
                        output_keys = list(schema.output_schema.keys())
                        logger.info(f"📤 Task '{folder_name}' will output: {output_keys}")

                task_counter["index"] += 1

                # Set task-specific output directory (maintaining directory isolation)
                task_output_dir = self.project_root / "tasks" / folder_name
                config.output_base_dir = task_output_dir
                config.screenshots_dir = task_output_dir / "screenshots"

                logger.info(f"📁 Task '{folder_name}' output directory: {task_output_dir}")

                return BugninjaClient(config=config)

            # Execute using BugninjaPipeline's run method with client factory
            logger.info(
                f"🚀 PipelineExecutor: Starting pipeline execution for {len(task_order)} tasks"
            )
            execution_results = await materialized_pipeline.run(
                mode="auto", client_factory=create_task_client
            )

            # Post-execution validation and logging
            logger.info(
                f"✅ PipelineExecutor: BugninjaPipeline execution completed with {len(execution_results)} results"
            )

            # Validate and log results for each task
            for i, result in enumerate(execution_results):
                task_desc = result.get("task_description", f"Task {i+1}")[:40]
                success = result.get("success", False)
                traversal_file = result.get("traversal_file")

                if success:
                    logger.info(f"✅ Task {i+1}: '{task_desc}...' completed successfully")
                    if traversal_file:
                        logger.info(f"📄 Task {i+1}: Traversal saved to {traversal_file}")
                    else:
                        logger.warning(
                            f"⚠️ Task {i+1}: No traversal file found - may affect parameter passing"
                        )
                else:
                    logger.warning(f"❌ Task {i+1}: '{task_desc}...' failed")

            # Get the last task's traversal file (target task)
            traversal_path = None
            if execution_results:
                last_result = execution_results[-1]
                if last_result.get("traversal_file"):
                    traversal_path = last_result["traversal_file"]
                    logger.info(f"🎯 PipelineExecutor: Target task traversal: {traversal_path}")
                else:
                    logger.warning("⚠️ PipelineExecutor: No traversal file from target task")

            # Update task metadata with the execution result
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_result = TaskExecutionResult(
                success=True,
                execution_time=execution_time,
                result=None,
                error_message=None,
                traversal_path=traversal_path,
            )

            # Update task metadata for the target task
            try:
                from bugninja.schemas.cli_schemas import TaskRunConfig
                from bugninja_cli.utils.task_executor import TaskExecutor

                # Create a default TaskRunConfig for metadata update
                task_run_config = TaskRunConfig()
                task_executor = TaskExecutor(task_run_config, self.project_root)
                task_executor._update_task_metadata(target_task, execution_result, "ai_navigated")
                logger.info(f"📝 Updated task metadata for '{target_task.name}' with AI run")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update task metadata: {e}")

            return execution_result

        except Exception as e:
            self.console.print(
                Panel(
                    f"❌ BugninjaPipeline execution failed: {str(e)}",
                    title="Execution Error",
                    border_style="red",
                )
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_result = TaskExecutionResult(
                success=False, execution_time=execution_time, result=None, error_message=str(e)
            )

            # Update task metadata even for failed runs
            try:
                from bugninja.schemas.cli_schemas import TaskRunConfig
                from bugninja_cli.utils.task_executor import TaskExecutor

                # Create a default TaskRunConfig for metadata update
                task_run_config = TaskRunConfig()
                task_executor = TaskExecutor(task_run_config, self.project_root)
                task_executor._update_task_metadata(target_task, execution_result, "ai_navigated")
                logger.info(f"📝 Updated task metadata for '{target_task.name}' with failed AI run")
            except Exception as metadata_error:
                logger.warning(f"⚠️ Failed to update task metadata: {metadata_error}")

            return execution_result

    def _load_task_run_config(self, task_payload: TaskSpec) -> TaskRunConfig:
        """Load task-specific run configuration from TOML file.

        Args:
            task_payload: TaskSpec containing the BugninjaTask

        Returns:
            TaskRunConfig: Configuration loaded from TOML file or defaults

        Notes:
            - For tasks with task_config_path: loads from TOML [run_config] section
            - For tasks without task_config_path: uses default values
            - Falls back to defaults if TOML loading fails
        """
        from bugninja.utils.logging_config import logger

        # Check if task has a config file path
        if hasattr(task_payload.task, "task_config_path") and task_payload.task.task_config_path:
            toml_path = task_payload.task.task_config_path
            if toml_path.exists():
                try:
                    # Use existing utility to load task run config
                    run_config = TaskExecutor._load_task_run_config(toml_path)
                    logger.info(
                        f"📋 PipelineExecutor: Loaded task-specific config from {toml_path.name}"
                    )
                    logger.info(
                        f"🖥️ PipelineExecutor: Viewport: {run_config.viewport_width}x{run_config.viewport_height}"
                    )
                    if run_config.user_agent:
                        logger.info(
                            f"🌐 PipelineExecutor: User agent: {run_config.user_agent[:50]}..."
                        )
                    return run_config
                except Exception as e:
                    logger.warning(
                        f"⚠️ PipelineExecutor: Failed to load config from {toml_path}: {e}"
                    )

        # Fallback to defaults
        default_config = TaskRunConfig()
        logger.info("📋 PipelineExecutor: Using default run configuration")
        return default_config

    def _display_dependency_tree(self, target_task: TaskInfo, task_order: List[str]) -> None:
        """Display dependency tree showing execution order.

        Args:
            target_task: The target task that was requested
            task_order: List of task folder names in execution order
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        # Create dependency tree display
        tree_lines = []
        tree_lines.append("📋 Dependency Execution Plan:")
        tree_lines.append("")

        for i, task_name in enumerate(task_order):
            is_target = task_name == target_task.folder_name
            is_last = i == len(task_order) - 1

            # Create tree structure
            if i == 0:
                prefix = "┌─"
            elif is_last:
                prefix = "└─"
            else:
                prefix = "├─"

            # Add task info
            if is_target:
                task_line = f"{prefix} 🎯 {task_name} (target task)"
                tree_lines.append(f"[bold green]{task_line}[/bold green]")
            else:
                task_line = f"{prefix} 📦 {task_name} (dependency)"
                tree_lines.append(f"[yellow]{task_line}[/yellow]")

            # Add connector for non-last items
            if not is_last:
                tree_lines.append("│")

        # Create panel with tree
        tree_text = Text.from_markup("\n".join(tree_lines))
        panel = Panel(
            tree_text,
            title="[bold blue]Task Execution Order[/bold blue]",
            border_style="blue",
            padding=(0, 1),
        )

        console.print()
        console.print(panel)
        console.print()

    def _display_current_task_status(
        self, current_task: str, current_index: int, total_tasks: int, target_task: TaskInfo
    ) -> None:
        """Display current task execution status.

        Args:
            current_task: Name of the currently executing task
            current_index: Current task index (1-based)
            total_tasks: Total number of tasks to execute
            target_task: The target task that was requested
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        # Determine task type
        is_target = current_task == target_task.folder_name
        task_type = "🎯 Target Task" if is_target else "📦 Dependency"

        # Create status message
        status_msg = f"{task_type}: [bold]{current_task}[/bold] ({current_index}/{total_tasks})"

        # Create panel
        panel = Panel(
            status_msg,
            title="[bold cyan]Now Executing[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

        console.print(panel)
