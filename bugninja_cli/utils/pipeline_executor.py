"""
CLI Pipeline Executor for Bugninja CLI commands.

This module provides a CLI wrapper for Pipeline functionality, enabling
dependency management and execution using the unified Pipeline API.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

from rich.console import Console
from rich.panel import Panel

from bugninja.api.pipeline import Pipeline, TaskRef, TaskSpec
from bugninja.schemas.cli_schemas import TaskExecutionResult, TaskInfo, TaskRunConfig
from bugninja.utils.logging_config import logger
from bugninja_cli.utils.task_executor import TaskExecutor
from bugninja_cli.utils.task_lookup import get_task_by_identifier
from bugninja_cli.utils.task_manager import TaskManager

if TYPE_CHECKING:
    from bugninja.api import BugninjaTask


class PipelineExecutor:
    """CLI wrapper for Pipeline functionality.

    This class provides a bridge between CLI TaskInfo objects and the
    Pipeline API, handling dependency resolution and execution with
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
        """Execute task with all dependencies using Pipeline.

        Args:
            target_task: The target task to execute
            task_manager: Task manager instance

        Returns:
            TaskExecutionResult: Result of the execution
        """
        from datetime import datetime

        start_time = datetime.now()

        # Convert to Pipeline with TaskRef nodes
        pipeline = self._convert_to_pipeline(target_task, task_manager)

        # Create resolver function that converts TaskRef to BugninjaTask
        def resolve_task_ref(task_ref: TaskRef) -> BugninjaTask:
            """Resolve TaskRef to BugninjaTask using task_manager."""
            task_info = get_task_by_identifier(task_manager, task_ref.identifier)
            if not task_info:
                raise ValueError(f"Could not resolve task by identifier: {task_ref.identifier}")

            from bugninja.api import BugninjaTask

            return BugninjaTask(task_config_path=task_info.toml_path)

        # Materialize TaskRef nodes to TaskSpec nodes
        try:
            materialized_pipeline = pipeline.materialize(resolve_task_ref)
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

        # Use Pipeline's built-in validation and execution
        try:
            # Note: Skipping upfront I/O validation for CLI mode as inputs are generated dynamically
            # materialized_pipeline.validate_io()

            # Show execution plan
            materialized_pipeline.print_plan()

            # Create client factory that generates task-specific clients
            from bugninja.api import BugninjaClient
            from bugninja.api.pipeline import TaskRef
            from bugninja.schemas.models import BugninjaConfig

            # Get the execution order from the materialized pipeline (with resolved TaskSpec objects)
            exec_list, _ = materialized_pipeline._build_exec_plan()

            # Map execution order to folder names using the dependency graph
            # Get the dependency graph with correct folder names in execution order
            all_tasks = self._build_dependency_graph(target_task, task_manager)
            task_order = [task.folder_name for task in all_tasks]

            logger.info(f"🗂️ Pipeline execution order: {' → '.join(task_order)}")

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

            # Execute using Pipeline's run method with client factory
            logger.info(
                f"🚀 PipelineExecutor: Starting pipeline execution for {len(task_order)} tasks"
            )
            execution_results = await materialized_pipeline.run(
                mode="auto", client_factory=create_task_client
            )

            # Post-execution validation and logging
            logger.info(
                f"✅ PipelineExecutor: Pipeline execution completed with {len(execution_results)} results"
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

            # Return success result with traversal path
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskExecutionResult(
                success=True,
                execution_time=execution_time,
                result=None,
                error_message=None,
                traversal_path=traversal_path,
            )

        except Exception as e:
            self.console.print(
                Panel(
                    f"❌ Pipeline execution failed: {str(e)}",
                    title="Execution Error",
                    border_style="red",
                )
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskExecutionResult(
                success=False, execution_time=execution_time, result=None, error_message=str(e)
            )

    def _convert_to_pipeline(self, target_task: TaskInfo, task_manager: TaskManager) -> Pipeline:
        """Convert CLI tasks to Pipeline with TaskRef objects.

        Args:
            target_task: The target task to execute
            task_manager: Task manager instance

        Returns:
            Pipeline: Configured pipeline with dependencies
        """
        pipeline = Pipeline()

        # Build dependency graph from target task
        all_tasks = self._build_dependency_graph(target_task, task_manager)

        # Add all tasks to pipeline
        for task in all_tasks:
            pipeline.testcase(task.folder_name, TaskRef(identifier=task.folder_name))

        # Set up dependency relationships
        for task in all_tasks:
            # Find dependencies for this task
            dependencies = self._get_task_dependencies(task, task_manager)
            if dependencies:
                parent_names = [dep.folder_name for dep in dependencies]
                pipeline.depends(task.folder_name, parent_names)

        return pipeline

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

    def _build_dependency_graph(
        self, target_task: TaskInfo, task_manager: TaskManager
    ) -> List[TaskInfo]:
        """Build complete dependency graph for target task.

        Args:
            target_task: The target task
            task_manager: Task manager instance

        Returns:
            List[TaskInfo]: All tasks in dependency order
        """
        # Use TaskExecutor's dependency resolution logic
        from bugninja.schemas.cli_schemas import TaskRunConfig

        dummy_config = TaskRunConfig()  # Create minimal config for dependency resolution
        temp_executor = TaskExecutor(task_run_config=dummy_config, project_root=self.project_root)

        try:
            # Get dependency plan
            plan = temp_executor._resolve_dependencies_toposort(target_task, task_manager)
            return plan
        except Exception as e:
            self.console.print(
                Panel(
                    f"❌ Failed to resolve dependencies: {str(e)}",
                    title="Dependency Resolution Error",
                    border_style="red",
                )
            )
            return [target_task]  # Fallback to just the target task

    def _get_task_dependencies(self, task: TaskInfo, task_manager: TaskManager) -> List[TaskInfo]:
        """Get dependencies for a specific task.

        Args:
            task: The task to get dependencies for
            task_manager: Task manager instance

        Returns:
            List[TaskInfo]: List of dependency tasks
        """
        dependencies = []

        # Load task configuration from TOML directly
        try:
            import tomli

            with open(task.toml_path, "rb") as f:
                task_config = tomli.load(f)
            dep_ids = task_config.get("task", {}).get("dependencies", [])
        except Exception:
            dep_ids = []

        for dep_id in dep_ids:
            dep_task = get_task_by_identifier(task_manager, str(dep_id))
            if dep_task:
                dependencies.append(dep_task)
        return dependencies
