"""Utility for incrementally persisting traversal data during agent runs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from browser_use.agent.views import AgentBrain  # type: ignore

from bugninja.schemas.pipeline import (
    BugninjaBrowserConfig,
    BugninjaExtendedAction,
    Traversal,
    TraversalStatus,
)


class TraversalRecorder:
    """Manage incremental traversal persistence with atomic writes."""

    def __init__(
        self,
        *,
        output_base_dir: Optional[Path],
        run_id: str,
        test_case: str,
        start_url: Optional[str],
        browser_config: BugninjaBrowserConfig,
        extra_instructions: List[str],
        secrets: Optional[Dict[str, str]],
        dependencies: List[str],
        input_schema: Optional[Dict[str, Any]],
        output_schema: Optional[Dict[str, Any]],
        available_files: Optional[List[Dict[str, Any]]],
        http_auth: Optional[Dict[str, str]],
    ) -> None:
        self.run_id = run_id
        self.test_case = test_case
        self.start_url = start_url
        self.browser_config = browser_config
        self.extra_instructions = extra_instructions
        self.secrets = secrets or {}
        self.dependencies = dependencies
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.available_files = available_files
        self.http_auth = http_auth
        self._latest_traversal: Optional[Traversal] = None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        traversal_dir = (
            (output_base_dir / "traversals") if output_base_dir else Path("./traversals")
        )
        traversal_dir.mkdir(parents=True, exist_ok=True)
        self.traversal_path = traversal_dir / f"traverse_{timestamp}_{run_id}.json"

    def record(
        self,
        *,
        brain_states: Dict[str, AgentBrain],
        actions: List[BugninjaExtendedAction],
        extracted_data: Optional[Dict[str, Any]],
        status: TraversalStatus,
    ) -> Traversal:
        """Persist the current traversal snapshot to disk."""
        actions_mapping: Dict[str, BugninjaExtendedAction] = {
            f"action_{idx}": action for idx, action in enumerate(actions)
        }

        traversal = Traversal(
            test_case=self.test_case,
            start_url=self.start_url,
            browser_config=self.browser_config,
            brain_states=brain_states,
            actions=actions_mapping,
            extra_instructions=self.extra_instructions,
            secrets=self.secrets,
            dependencies=self.dependencies,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            extracted_data=extracted_data or {},
            available_files=self.available_files,
            http_auth=self.http_auth,
            status=status,
        )

        self._atomic_write(traversal.model_dump(mode="json"))
        self._latest_traversal = traversal
        return traversal

    def get_latest_traversal(self) -> Optional[Traversal]:
        """Return the most recently recorded traversal object."""
        return self._latest_traversal

    def _atomic_write(self, payload: Dict[str, Any]) -> None:
        temp_path = self.traversal_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
        temp_path.replace(self.traversal_path)


__all__ = ["TraversalRecorder"]
