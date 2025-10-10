from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from bugninja.schemas import TaskRunConfig
from bugninja.schemas.models import BugninjaTask
from bugninja.utils.logging_config import logger

if TYPE_CHECKING:
    from bugninja.api.client import BugninjaClient


class TaskRef(BaseModel):
    """Reference to a task by folder name or CUID."""

    identifier: str = Field(description="Task folder name or CUID")


class TaskSpec(BaseModel):
    """Inline task specification using a BugninjaTask instance."""

    task: BugninjaTask = Field(description="In-code BugninjaTask definition")


class _Node(BaseModel):
    task: Union[TaskRef, TaskSpec]
    depends_on: List[str] = Field(default_factory=list)  # List of parent task names/descriptions


class Pipeline:
    def __init__(
        self,
        default_run_config: Optional[TaskRunConfig] = None,
    ) -> None:
        self._nodes: List[_Node] = []
        # DAG-first API state (optional)
        self._dag_nodes: Dict[str, Union[TaskRef, TaskSpec]] = {}
        self._dag_edges: Dict[str, List[str]] = {}  # child_id -> [parent_ids]
        # Default run configuration for spec-only pipelines
        self._default_run_config: Optional[TaskRunConfig] = default_run_config

    # ---------------- Internal helpers (separation of concerns) ----------------
    def _collect_child_inputs(self, child: Union[TaskRef, TaskSpec]) -> Tuple[Set[str], str]:
        """Collect input schema keys from a TaskSpec or TaskRef."""
        if isinstance(child, TaskRef):
            # For TaskRef, we can't get schema without CLI dependencies
            # This should only be called from CLI context
            return set(), child.identifier
        schema = child.task.io_schema.input_schema or {} if child.task.io_schema else {}
        name = getattr(child.task, "name", None) or child.task.description[:40]
        return set(schema.keys()), name

    def _collect_parent_outputs(self, parent: Union[TaskRef, TaskSpec]) -> Tuple[Set[str], str]:
        """Collect output schema keys from a TaskSpec or TaskRef."""
        if isinstance(parent, TaskRef):
            # For TaskRef, we can't get schema without CLI dependencies
            # This should only be called from CLI context
            return set(), parent.identifier
        oschema = parent.task.io_schema.output_schema or {} if parent.task.io_schema else {}
        return set(oschema.keys()), getattr(parent.task, "name", None) or ""

    def _build_exec_plan(
        self,
    ) -> Tuple[List[Tuple[str, Union[TaskRef, TaskSpec]]], Dict[str, List[str]]]:
        """Build execution plan for pipeline."""
        order = self._toposort()
        exec_list: List[Tuple[str, Union[TaskRef, TaskSpec]]] = []
        parents_map: Dict[str, List[str]] = {}
        edges = self._resolve_all()

        for child_key, parent_key in edges:
            parents_map.setdefault(child_key, []).append(parent_key)

        if self._dag_nodes:
            for id_, task in self._dag_nodes.items():
                key = self._node_key(_Node(task=task, depends_on=[]))
                if isinstance(task, TaskSpec):
                    # Update the task's dependencies based on Pipeline's dependency graph
                    task_deps = self._dag_edges.get(id_, [])
                    # Create a new TaskSpec with updated dependencies
                    updated_task = TaskSpec(
                        task=task.task.model_copy(update={"dependencies": task_deps})
                    )
                    exec_list.append((key, updated_task))
                else:
                    # TaskRef - pass through as-is
                    exec_list.append((key, task))
        else:
            key_to_node = {self._node_key(n): n for n in self._nodes}
            for key in order:
                node = key_to_node.get(key)
                if node:
                    exec_list.append((key, node.task))
                else:
                    raise ValueError(f"Unrecognized plan element: {key}")
        return exec_list, parents_map

    def add(
        self, task: Union[TaskRef, TaskSpec], depends_on: Optional[List[str]] = None
    ) -> "Pipeline":
        """Add a task to the pipeline with optional dependencies."""
        self._nodes.append(_Node(task=task, depends_on=depends_on or []))
        return self

    # DAG-first API
    def testcase(self, id: str, task: Union[TaskRef, TaskSpec]) -> "Pipeline":
        """Add a testcase to the DAG."""
        if id in self._dag_nodes:
            raise ValueError(f"Duplicate testcase id: {id}")
        self._dag_nodes[id] = task
        self._dag_edges.setdefault(id, [])
        return self

    def depends(
        self,
        child: str,
        parents: List[str],
    ) -> "Pipeline":
        if child not in self._dag_nodes:
            raise ValueError(f"Unknown child testcase id: {child}")
        for p in parents:
            if p not in self._dag_nodes:
                raise ValueError(f"Unknown parent testcase id: {p}")
        # record edges
        self._dag_edges.setdefault(child, [])
        for p in parents:
            if p not in self._dag_edges[child]:
                self._dag_edges[child].append(p)
        return self

    def materialize(self, resolver: Callable[[TaskRef], BugninjaTask]) -> "Pipeline":
        """Materialize TaskRef nodes to TaskSpec nodes using a resolver function.

        This method creates a new Pipeline where all TaskRef nodes are replaced
        with TaskSpec nodes containing resolved BugninjaTask instances.

        Args:
            resolver: Function that takes a TaskRef and returns a BugninjaTask

        Returns:
            Pipeline: New pipeline with TaskSpec nodes instead of TaskRef nodes
        """
        materialized = Pipeline(default_run_config=self._default_run_config)

        # Materialize DAG nodes
        if self._dag_nodes:
            for id_, task in self._dag_nodes.items():
                if isinstance(task, TaskRef):
                    # Resolve TaskRef to BugninjaTask, then wrap as TaskSpec
                    resolved_task = resolver(task)
                    materialized._dag_nodes[id_] = TaskSpec(task=resolved_task)
                else:
                    # Already a TaskSpec, copy as-is
                    materialized._dag_nodes[id_] = task

            # Copy edges
            materialized._dag_edges = self._dag_edges.copy()
        else:
            # Materialize chain nodes
            for node in self._nodes:
                if isinstance(node.task, TaskRef):
                    # Resolve TaskRef to BugninjaTask, then wrap as TaskSpec
                    resolved_task = resolver(node.task)
                    materialized._nodes.append(
                        _Node(task=TaskSpec(task=resolved_task), depends_on=node.depends_on.copy())
                    )
                else:
                    # Already a TaskSpec, copy as-is
                    materialized._nodes.append(
                        _Node(task=node.task, depends_on=node.depends_on.copy())
                    )

        return materialized

    def _node_key(self, node: _Node) -> str:
        """Generate unique key for a node."""
        if isinstance(node.task, TaskRef):
            return f"ref::{node.task.identifier}"
        # TaskSpec: stable hash from description + allowed_domains + max_steps
        import hashlib

        payload = f"{node.task.task.description}|{node.task.task.allowed_domains}|{node.task.task.max_steps}"
        return f"spec::{hashlib.md5(payload.encode()).hexdigest()}"

    def _resolve_all(self) -> List[Tuple[str, str]]:
        """Resolve all dependencies to internal node keys."""
        # DAG-mode
        if self._dag_nodes:
            edges: List[Tuple[str, str]] = []
            # Map ids to keys
            id_to_key: Dict[str, str] = {}
            for id_, task in self._dag_nodes.items():
                id_to_key[id_] = self._node_key(_Node(task=task, depends_on=[]))

            for child_id, parent_ids in self._dag_edges.items():
                child_key = id_to_key[child_id]
                for pid in parent_ids:
                    edges.append((child_key, id_to_key[pid]))
            return edges
        # Chain-mode
        edges = []
        # Build alias map from TaskSpec nodes
        aliases: Dict[str, str] = {}
        for node in self._nodes:
            key = self._node_key(node)
            if isinstance(node.task, TaskSpec):
                name = getattr(node.task.task, "name", None) or node.task.task.description[:32]
            else:
                name = node.task.identifier
            aliases[name] = key
        for node in self._nodes:
            child_key = self._node_key(node)
            for dep in node.depends_on:
                parent_key = aliases.get(dep)
                if not parent_key:
                    # Try to find by description match
                    for other_node in self._nodes:
                        if isinstance(other_node.task, TaskSpec):
                            if (
                                other_node.task.task.description.startswith(dep)
                                or getattr(other_node.task.task, "name", "") == dep
                            ):
                                parent_key = self._node_key(other_node)
                                break
                        else:
                            if other_node.task.identifier == dep:
                                parent_key = self._node_key(other_node)
                                break
                if parent_key:
                    edges.append((child_key, parent_key))
        return edges

    def _toposort(self) -> List[str]:
        """Topological sort of tasks."""
        # Build set of all node keys
        if self._dag_nodes:
            ids: Set[str] = set(
                self._node_key(_Node(task=t, depends_on=[])) for t in self._dag_nodes.values()
            )
        else:
            ids = set(self._node_key(n) for n in self._nodes)

        # Build graph (dep -> child)
        edges = self._resolve_all()
        outgoing: Dict[str, List[str]] = {i: [] for i in ids}
        indeg: Dict[str, int] = {i: 0 for i in ids}
        for child, parent in edges:
            outgoing.setdefault(parent, []).append(child)
            indeg[child] = indeg.get(child, 0) + 1
            indeg.setdefault(parent, indeg.get(parent, 0))

        # Kahn's algorithm
        queue: List[str] = [i for i, d in indeg.items() if d == 0]
        order: List[str] = []
        while queue:
            u = queue.pop()
            order.append(u)
            for v in outgoing.get(u, []):
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)
        if len(order) != len(ids):
            raise ValueError("Cyclic dependency detected in Pipeline")
        return order

    def validate_io(self) -> "Pipeline":
        """Validate I/O schema compatibility between tasks."""
        # DAG-mode validation
        if self._dag_nodes:
            for child_id, child_task in self._dag_nodes.items():
                # child inputs
                child_inputs, child_name = self._collect_child_inputs(child_task)

                required: Set[str] = set()
                per_parent_missing: Dict[str, List[str]] = {}
                for parent_id in self._dag_edges.get(child_id, []):
                    parent_keys, display_name = self._collect_parent_outputs(
                        self._dag_nodes[parent_id]
                    )

                    required |= parent_keys
                    missing_for_parent = sorted(list(parent_keys - child_inputs))
                    if missing_for_parent:
                        per_parent_missing[display_name] = missing_for_parent

                missing = required - child_inputs
                if missing:
                    raise ValueError(
                        f"I/O schema mismatch for '{child_name}'. Missing keys: {sorted(list(missing))}. Per-parent: {per_parent_missing}"
                    )
            return self

        # Chain-mode validation
        for node in self._nodes:
            # Collect child input keys
            child_inputs, child_name = self._collect_child_inputs(node.task)

            required = set()
            per_parent_missing = {}
            for dep in node.depends_on:
                parent_outputs: Set[str] = set()
                display_name = dep
                for cand in self._nodes:
                    if isinstance(cand.task, TaskSpec):
                        if getattr(
                            cand.task.task, "name", None
                        ) == dep or cand.task.task.description.startswith(dep):
                            parent_outputs, display_name = self._collect_parent_outputs(cand.task)
                            break
                    else:
                        if cand.task.identifier == dep:
                            parent_outputs, display_name = self._collect_parent_outputs(cand.task)
                            break

                required |= parent_outputs
                missing_for_parent = sorted(list(parent_outputs - child_inputs))
                if missing_for_parent:
                    per_parent_missing[display_name] = missing_for_parent

            missing = required - child_inputs
            if missing:
                raise ValueError(
                    f"I/O schema mismatch for '{child_name}'. Missing keys: {sorted(list(missing))}. Per-parent: {per_parent_missing}"
                )
        return self

    def print_plan(self) -> "Pipeline":
        """Print execution plan."""
        order = self._toposort()
        # Resolve to names where possible
        names: List[str] = []
        if self._dag_nodes:
            key_to_pretty: Dict[str, str] = {}
            for id_, task in self._dag_nodes.items():
                key = self._node_key(_Node(task=task, depends_on=[]))
                if isinstance(task, TaskSpec):
                    nm = getattr(task.task, "name", None) or task.task.description[:40]
                else:
                    nm = task.identifier
                key_to_pretty[key] = nm
            names = [key_to_pretty.get(k, k) for k in order]
        else:
            key_to_node = {self._node_key(n): n for n in self._nodes}
            for key in order:
                n = key_to_node.get(key)
                if n:
                    if isinstance(n.task, TaskSpec):
                        nm = getattr(n.task.task, "name", None) or n.task.task.description[:40]
                    else:
                        nm = n.task.identifier
                    names.append(nm)
                else:
                    names.append(key)

        return self

    async def run(
        self,
        mode: str = "auto",
        client: Optional["BugninjaClient"] = None,
        client_factory: Optional[Callable[[Union[TaskRef, TaskSpec]], "BugninjaClient"]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the pipeline (TaskSpec only).

        Args:
            mode: Execution mode ('agent', 'replay', 'auto')
            client: Optional pre-configured BugninjaClient (for simple library usage)
            client_factory: Optional factory function that creates a task-specific client (for CLI usage)

        Returns:
            List of execution results with traversal paths and metadata for each task
        """
        if mode not in {"agent", "replay", "auto"}:
            raise ValueError("mode must be one of {'agent','replay','auto'}")

        if mode == "replay":
            raise ValueError("Replay mode is not supported for TaskSpec-only pipelines")

        exec_list, parents_map = self._build_exec_plan()

        # Check if we have any TaskRef tasks - they need CLI handling
        for key, payload in exec_list:
            if isinstance(payload, TaskRef):
                raise ValueError(
                    "TaskRef tasks require CLI context. Use PipelineExecutor for CLI tasks."
                )

        async def _run() -> List[Dict[str, Any]]:

            from bugninja.api.client import BugninjaClient

            # Keep track of outputs produced by executed tasks for use by their children
            produced_outputs: Dict[str, Dict[str, str]] = {}

            # Keep track of execution results
            execution_results: List[Dict[str, Any]] = []

            # Determine execution mode based on parameters
            if client_factory is not None:
                # CLI mode: each task gets its own client
                execution_results = await self._execute_with_client_factory(
                    client_factory, exec_list, parents_map, produced_outputs
                )
            elif client is not None:
                # Library mode with provided client
                execution_results = await self._execute_with_client(
                    client, exec_list, parents_map, produced_outputs
                )
            else:
                # Library mode with default client
                async with BugninjaClient() as default_client:
                    execution_results = await self._execute_with_client(
                        default_client, exec_list, parents_map, produced_outputs
                    )

            return execution_results

        return await _run()

    async def _execute_with_client_factory(
        self,
        client_factory: Callable[[Union[TaskRef, TaskSpec]], "BugninjaClient"],
        exec_list: List[Tuple[str, Union[TaskRef, TaskSpec]]],
        parents_map: Dict[str, List[str]],
        produced_outputs: Dict[str, Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Execute pipeline tasks with task-specific clients from factory."""
        execution_results: List[Dict[str, Any]] = []

        for idx, (key, payload) in enumerate(exec_list):
            # At this point, payload should only be TaskSpec due to earlier check
            assert isinstance(payload, TaskSpec), "Only TaskSpec should reach this point"

            # Create task-specific client
            task_client = client_factory(payload)

            # Execute single task with its own client
            result = await self._execute_single_task(
                task_client, key, payload, parents_map, produced_outputs
            )
            execution_results.append(result)

        return execution_results

    async def _execute_with_client(
        self,
        client: "BugninjaClient",
        exec_list: List[Tuple[str, Union[TaskRef, TaskSpec]]],
        parents_map: Dict[str, List[str]],
        produced_outputs: Dict[str, Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """Execute pipeline tasks with the provided client."""
        execution_results: List[Dict[str, Any]] = []

        for idx, (key, payload) in enumerate(exec_list):
            # At this point, payload should only be TaskSpec due to earlier check
            assert isinstance(payload, TaskSpec), "Only TaskSpec should reach this point"

            # Execute single task
            result = await self._execute_single_task(
                client, key, payload, parents_map, produced_outputs
            )
            execution_results.append(result)

        return execution_results

    async def _execute_single_task(
        self,
        client: "BugninjaClient",
        key: str,
        payload: TaskSpec,
        parents_map: Dict[str, List[str]],
        produced_outputs: Dict[str, Dict[str, str]],
    ) -> Dict[str, Any]:
        """Execute a single task in the pipeline.

        Returns:
            Dict with task execution metadata including traversal_file path
        """
        parents = parents_map.get(key, [])

        # Enhanced input merging with comprehensive validation and logging
        merged_inputs: Dict[str, str] = {}

        logger.info(
            f"🔗 Pipeline: Processing task '{payload.task.description[:40]}...' with {len(parents)} parent dependencies"
        )

        if parents:
            logger.info(f"📤 Pipeline: Parent keys available for merging: {list(parents)}")
        else:
            logger.info("📤 Pipeline: Task has no parent dependencies")

        # Build merged inputs from parents' extracted_data
        for parent_key in parents:
            parent_outputs: Dict[str, str] = {}
            # Prefer outputs collected during this run
            if parent_key in produced_outputs:
                parent_outputs = produced_outputs[parent_key]
                logger.info(
                    f"📊 Pipeline: Found {len(parent_outputs)} outputs from parent '{parent_key}': {list(parent_outputs.keys())}"
                )

                # Log each parent output for debugging
                for out_key, out_value in parent_outputs.items():
                    logger.info(f"📋 Pipeline: Parent output {out_key} = {out_value}")
            else:
                logger.warning(
                    f"⚠️ Pipeline: No outputs found from parent '{parent_key}' - dependency may have failed"
                )

            # Merge with conflict detection and enhanced logging
            for k_inp, v_inp in parent_outputs.items():
                if k_inp in merged_inputs and merged_inputs[k_inp] != v_inp:
                    from rich.console import Console

                    error_msg = (
                        f"Conflict for input key '{k_inp}': '{merged_inputs[k_inp]}' vs '{v_inp}'"
                    )
                    Console().print(f"⛔ {error_msg}")
                    logger.error(f"⛔ Pipeline: Input conflict detected - {error_msg}")
                    raise RuntimeError(f"Pipeline execution stopped: {error_msg}")

                merged_inputs[k_inp] = v_inp
                logger.info(f"✅ Pipeline: Merged input {k_inp} = {v_inp}")

        logger.info(f"📥 Pipeline: Final merged inputs for task: {list(merged_inputs.keys())}")

        # Enhanced validation with comprehensive logging
        required_keys: Set[str] = set()
        child_secrets_keys: Set[str] = set()

        if payload.task.io_schema and payload.task.io_schema.input_schema:
            required_keys = set(payload.task.io_schema.input_schema.keys())
            logger.info(
                f"🔍 Pipeline: Task requires {len(required_keys)} inputs: {list(required_keys)}"
            )
        else:
            logger.info("🔍 Pipeline: Task has no input schema requirements")

        if payload.task.secrets:
            child_secrets_keys = set(payload.task.secrets.keys())
            logger.info(f"🔐 Pipeline: Task has {len(child_secrets_keys)} secrets configured")
        else:
            logger.info("🔐 Pipeline: Task has no secrets configured")

        # Check for conflicts between input_schema and secrets
        conflicts = required_keys & child_secrets_keys
        if conflicts:
            from rich.console import Console

            error_msg = f"Key conflicts between input_schema and secrets: {sorted(conflicts)}"
            Console().print(f"⛔ {error_msg}")
            logger.error(f"⛔ Pipeline: Schema conflict - {error_msg}")
            raise RuntimeError(f"Pipeline execution stopped: {error_msg}")

        # Validate all required inputs are available
        missing_required = [k for k in required_keys if k not in merged_inputs]
        if missing_required:
            from rich.console import Console

            error_msg = f"Missing required inputs for child: {sorted(missing_required)}"
            Console().print(f"⛔ {error_msg}")
            logger.error(f"⛔ Pipeline: Missing inputs - {error_msg}")
            logger.info(f"📋 Pipeline: Available inputs: {list(merged_inputs.keys())}")
            logger.info(f"📋 Pipeline: Required inputs: {list(required_keys)}")
            raise RuntimeError(f"Pipeline execution stopped: {error_msg}")

        # Log successful validation
        if required_keys:
            logger.info(f"✅ Pipeline: All {len(required_keys)} required inputs satisfied")

        logger.info(f"🚀 Pipeline: Executing task with {len(merged_inputs)} runtime inputs")

        # Execute the task
        from rich.console import Console

        Console().print(f"🔄 Executing task: {payload.task.description[:50]}...")

        # Pass merged inputs separately without modifying task secrets
        result = await client.run_task(
            payload.task,
            runtime_inputs=merged_inputs,
        )

        if not result.success:
            # Surface detailed error information to aid debugging
            err = result.error
            error_msg = (
                str(err) if err is not None else "Task failed with no additional error details"
            )

            from rich.console import Console

            Console().print(f"❌ Task failed: {error_msg}")

            # Also hint where artifacts might be
            if result.traversal_file:
                Console().print(f"🧭 Last traversal file: {result.traversal_file}")
            if result.screenshots_dir:
                Console().print(f"🖼️ Screenshots dir: {result.screenshots_dir}")

            # Raise exception to stop pipeline execution
            raise RuntimeError(f"Pipeline execution stopped: {error_msg}")

        # Record produced outputs for children with robust state management
        extracted_outputs: Dict[str, str] = {}

        # Primary: Try to extract from result.traversal (standard path)
        trav = result.traversal
        if trav is not None:
            exd = getattr(trav, "extracted_data", None)
            if exd:
                try:
                    extracted_outputs = dict(exd)
                    logger.info(
                        f"🔗 Pipeline: Extracted {len(extracted_outputs)} outputs from traversal for task '{payload.task.description[:40]}...'"
                    )
                    for out_key, out_value in extracted_outputs.items():
                        logger.info(f"📊 Pipeline output: {out_key} = {out_value}")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Pipeline: Failed to convert traversal extracted_data to dict: {e}"
                    )
                    extracted_outputs = {}
            else:
                logger.warning(
                    f"⚠️ Pipeline: Traversal exists but has no extracted_data for task '{payload.task.description[:40]}...'"
                )
        else:
            logger.warning(
                f"⚠️ Pipeline: No traversal object in result for task '{payload.task.description[:40]}...'"
            )

        # Fallback: Try to load traversal from file if available
        if not extracted_outputs and result.traversal_file:
            logger.info(
                f"🔄 Pipeline: Attempting fallback extraction from traversal file: {result.traversal_file}"
            )
            try:
                import json
                from pathlib import Path

                traversal_path = Path(result.traversal_file)
                if traversal_path.exists():
                    with open(traversal_path, "r") as f:
                        traversal_data = json.load(f)
                        file_extracted_data = traversal_data.get("extracted_data", {})
                        if file_extracted_data:
                            extracted_outputs = dict(file_extracted_data)
                            logger.info(
                                f"✅ Pipeline: Recovered {len(extracted_outputs)} outputs from traversal file"
                            )
                            for out_key, out_value in extracted_outputs.items():
                                logger.info(
                                    f"📊 Pipeline recovered output: {out_key} = {out_value}"
                                )
                        else:
                            logger.warning(
                                "⚠️ Pipeline: Traversal file exists but contains no extracted_data"
                            )
                else:
                    logger.warning(
                        f"⚠️ Pipeline: Traversal file path exists in result but file not found: {traversal_path}"
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ Pipeline: Failed to load traversal from file {result.traversal_file}: {e}"
                )

        # Final validation and storage
        if extracted_outputs:
            produced_outputs[key] = extracted_outputs
            logger.info(
                f"✅ Pipeline: Successfully stored {len(extracted_outputs)} outputs for downstream tasks"
            )
        else:
            produced_outputs[key] = {}
            logger.warning(
                f"⚠️ Pipeline: No extracted outputs found for task '{payload.task.description[:40]}...' - downstream tasks may fail"
            )

        # Return execution metadata
        return {
            "task_description": payload.task.description,
            "success": result.success,
            "traversal_file": result.traversal_file,
            "screenshots_dir": result.screenshots_dir,
            "steps_completed": result.steps_completed,
            "total_steps": result.total_steps,
        }
