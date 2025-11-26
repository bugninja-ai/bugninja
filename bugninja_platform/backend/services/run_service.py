"""Run service for reading and transforming test run data.

This service handles reading traversal JSON files and transforming them
into the format expected by the frontend for polling and display.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class RunService:
    """Service for managing test run data from traversal files.

    This service provides methods for:
    - Finding traversal files by run ID
    - Reading and parsing traversal JSON
    - Transforming to frontend-expected format
    - Determining run status

    Attributes:
        project_root (Path): Root directory of the Bugninja project
    """

    def __init__(self, project_root: Path):
        """Initialize RunService.

        Args:
            project_root (Path): Root directory of the Bugninja project
        """
        self.project_root = project_root
        self.tasks_dir = project_root / "tasks"

    def find_traversal_file(self, run_id: str) -> Optional[Path]:
        """Find traversal file by run ID.

        Searches all task traversal directories for a file ending with the run ID.

        Args:
            run_id (str): Run identifier

        Returns:
            Optional[Path]: Path to traversal file, or None if not found
        """
        tasks_dir = self.project_root / "tasks"
        if not tasks_dir.exists():
            return None

        # Search all task directories for traversal files
        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            traversals_dir = task_dir / "traversals"
            if not traversals_dir.exists():
                continue

            # Look for file ending with run_id.json
            for traversal_file in traversals_dir.glob(f"*_{run_id}.json"):
                return traversal_file

        return None

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get test run details by run ID.

        Reads the traversal file FRESH on every request and transforms it
        to the format expected by the frontend for polling. This supports
        incremental file updates during task execution.

        Args:
            run_id (str): Run identifier

        Returns:
            Optional[Dict]: Run details in frontend format, or None if not found
        """
        # Find traversal file - search on EVERY request for fresh data
        traversal_file = self.find_traversal_file(run_id)

        # If file doesn't exist yet, return RUNNING state with minimal data
        if not traversal_file or not traversal_file.exists():
            return self._create_running_response(run_id)

        # Read and transform traversal file - ALWAYS read fresh from disk
        try:
            with open(traversal_file, "r") as f:
                traversal_data = json.load(f)

            return self._transform_traversal_to_run(traversal_data, run_id, traversal_file)

        except (json.JSONDecodeError, Exception) as e:
            # File is being written (partial JSON) - return RUNNING state
            # This can happen if we read while the library is writing
            print(f"Error reading traversal file (likely being written): {e}")
            return self._create_running_response(run_id)

    def _create_running_response(self, run_id: str) -> Dict[str, Any]:
        """Create a minimal RUNNING response when file doesn't exist yet.

        Args:
            run_id (str): Run identifier

        Returns:
            Dict: Minimal run data with RUNNING state
        """
        return {
            "id": run_id,
            "test_case": None,
            "current_state": "RUNNING",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "run_type": "AGENTIC",
            "origin": "WEB_UI",
            "browser_config": None,
            "brain_states": [],
            "run_gif": None,
            "test_traversal_id": run_id,
        }

    def _read_task_toml(self, task_dir: Path) -> Optional[Dict[str, Any]]:
        """Read task TOML file for a given task directory.

        Args:
            task_dir (Path): Task directory path

        Returns:
            Optional[Dict]: Parsed TOML data, or None if not found
        """
        # Find task_*.toml file
        toml_files = list(task_dir.glob("task_*.toml"))
        if not toml_files:
            return None

        toml_file = toml_files[0]
        try:
            with open(toml_file, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"Error reading TOML file {toml_file}: {e}")
            return None

    def _transform_traversal_to_run(
        self, traversal_data: Dict[str, Any], run_id: str, traversal_file: Path
    ) -> Dict[str, Any]:
        """Transform traversal JSON to frontend run format.

        Args:
            traversal_data (Dict): Parsed traversal JSON
            run_id (str): Run identifier
            traversal_file (Path): Path to traversal file

        Returns:
            Dict: Transformed run data
        """
        # Determine task name from file path
        task_name = traversal_file.parent.parent.name
        task_dir = traversal_file.parent.parent

        # Read clean test description and goal from TOML file
        toml_data = self._read_task_toml(task_dir)
        test_description = ""
        test_goal = ""
        if toml_data:
            # Description comes from the description field
            test_description = toml_data.get("task", {}).get("description", "")
            # Goal is just the description itself - no extra instructions shown in UI
            test_goal = test_description

        # Determine current state based on presence of "done" action
        actions = traversal_data.get("actions", {})
        has_done = any(
            action_data.get("action", {}).get("done") is not None
            for action_data in actions.values()
        )

        current_state = "FINISHED" if has_done else "RUNNING"

        # Get file times
        file_stat = traversal_file.stat()
        # For started_at, try to get creation time, fallback to modified time
        started_at = datetime.fromtimestamp(
            getattr(file_stat, "st_birthtime", file_stat.st_mtime)
        ).isoformat()

        # finished_at is only set if task is done
        finished_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat() if has_done else None

        # Transform brain states (pass task_name for screenshot URLs)
        brain_states = self._transform_brain_states(traversal_data, task_name)

        # Get browser config from traversal
        browser_config_data = traversal_data.get("browser_config", {})

        # Create test case reference with clean data from TOML
        test_case = {
            "id": task_name,
            "test_name": task_name,
            "test_description": test_description,
            "test_goal": test_goal,
        }

        return {
            "id": run_id,
            "test_case": test_case,
            "current_state": current_state,
            "started_at": started_at,
            "finished_at": finished_at,
            "run_type": "AGENTIC",
            "origin": "WEB_UI",
            "browser_config": {
                "id": f"{task_name}_config",
                "browser_config": browser_config_data,
            },
            "brain_states": brain_states,
            "run_gif": None,  # TODO: Add GIF support if available
            "test_traversal_id": run_id,
        }

    def _transform_brain_states(
        self, traversal_data: Dict[str, Any], task_name: str
    ) -> List[Dict[str, Any]]:
        """Transform brain states from traversal format to frontend format.

        Args:
            traversal_data (Dict): Parsed traversal JSON
            task_name (str): Name of the task (for screenshot URLs)

        Returns:
            List[Dict]: Transformed brain states with history elements
        """
        brain_states_dict = traversal_data.get("brain_states", {})
        actions_dict = traversal_data.get("actions", {})

        # Group actions by brain_state_id
        actions_by_brain_state: Dict[str, List[Dict[str, Any]]] = {}
        for action_key, action_data in actions_dict.items():
            brain_state_id = action_data.get("brain_state_id")
            if brain_state_id:
                if brain_state_id not in actions_by_brain_state:
                    actions_by_brain_state[brain_state_id] = []
                actions_by_brain_state[brain_state_id].append(action_data)

        # Transform brain states
        brain_states = []
        for brain_state_id, brain_state_data in brain_states_dict.items():
            # Get actions for this brain state
            brain_state_actions = actions_by_brain_state.get(brain_state_id, [])

            # Transform actions to history_elements format
            history_elements: List[Dict[str, Any]] = []
            for idx, action_data in enumerate(brain_state_actions):
                history_element = self._transform_action_to_history_element(
                    action_data, idx, task_name
                )
                history_elements.append(history_element)

            # Create brain state object
            brain_state = {
                "id": brain_state_id,
                "evaluation_previous_goal": brain_state_data.get("evaluation_previous_goal", ""),
                "next_goal": brain_state_data.get("next_goal", ""),
                "memory": brain_state_data.get("memory", ""),
                "history_elements": history_elements,
            }
            brain_states.append(brain_state)

        return brain_states

    def _transform_action_to_history_element(
        self, action_data: Dict[str, Any], idx: int, task_name: str
    ) -> Dict[str, Any]:
        """Transform a single action to history_element format.

        Args:
            action_data (Dict): Action data from traversal
            idx (int): Index of action in brain state
            task_name (str): Name of the task (for screenshot URLs)

        Returns:
            Dict: Transformed history element
        """
        action_raw = action_data.get("action", {})

        # Clean up action: only include non-null action types
        # The traversal has all action types as keys, but only one has a value
        action = {}
        for action_type, action_value in action_raw.items():
            if action_value is not None:
                action[action_type] = action_value

        # Get screenshot filename and convert to URL
        # Screenshots are stored at: tasks/{task_name}/screenshots/{run_id}/file.png
        screenshot = action_data.get("screenshot_filename")
        if screenshot:
            # Convert relative path to URL path (NO leading slash - frontend adds it)
            # From: "screenshots/ig9k2qu035xdz8x8fgqmcvr4/001_go_to_url.png"
            # To: "tasks/1_simple_navigation/screenshots/ig9k2qu035xdz8x8fgqmcvr4/001_go_to_url.png"
            # Frontend will prepend BASE_DOMAIN/ to make full URL
            screenshot = f"tasks/{task_name}/{screenshot}"

        return {
            "id": f"action_{idx}",
            "history_element_state": "SUCCESS",  # TODO: Determine from action result
            "action": action,
            "screenshot": screenshot,
            "dom_element_data": action_data.get("dom_element_data"),
        }

    def list_all_runs(self) -> List[Dict[str, Any]]:
        """List all test runs across all test cases.

        Scans all task directories for traversal files and returns
        a summary list of all runs with basic metadata.

        Returns:
            List[Dict]: List of run summaries with metadata
        """
        runs = []

        if not self.tasks_dir.exists():
            return runs

        # Iterate through all task directories
        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            traversals_dir = task_dir / "traversals"
            if not traversals_dir.exists():
                continue

            # Process all traversal files in this task
            for traversal_file in traversals_dir.glob("*.json"):
                run_summary = self._create_run_summary(traversal_file, task_dir.name)
                if run_summary:
                    runs.append(run_summary)

        # Sort by started_at descending (newest first)
        runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return runs

    def list_runs_for_test_case(self, test_case_id: str) -> List[Dict[str, Any]]:
        """List all test runs for a specific test case.

        Args:
            test_case_id (str): Test case identifier (task name or folder name)

        Returns:
            List[Dict]: List of run summaries for the test case
        """
        runs = []

        if not self.tasks_dir.exists():
            return runs

        # Find the task directory
        task_dir = None
        for potential_task_dir in self.tasks_dir.iterdir():
            if not potential_task_dir.is_dir():
                continue
            # Match by folder name or task name
            if potential_task_dir.name == test_case_id or test_case_id in potential_task_dir.name:
                task_dir = potential_task_dir
                break

        if not task_dir:
            return runs

        traversals_dir = task_dir / "traversals"
        if not traversals_dir.exists():
            return runs

        # Process all traversal files
        for traversal_file in traversals_dir.glob("*.json"):
            run_summary = self._create_run_summary(traversal_file, task_dir.name)
            if run_summary:
                runs.append(run_summary)

        # Sort by started_at descending (newest first)
        runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return runs

    def _create_run_summary(self, traversal_file: Path, task_name: str) -> Optional[Dict[str, Any]]:
        """Create a summary of a test run from traversal file.

        Args:
            traversal_file (Path): Path to traversal JSON file
            task_name (str): Name of the task

        Returns:
            Optional[Dict]: Run summary or None if file can't be read
        """
        try:
            # Extract run_id from filename (format: anything_RUNID.json)
            run_id = traversal_file.stem.split("_")[-1]

            # Get file metadata
            file_stat = traversal_file.stat()
            started_at = datetime.fromtimestamp(
                getattr(file_stat, "st_birthtime", file_stat.st_mtime)
            ).isoformat()

            # Try to read file to get state
            try:
                with open(traversal_file, "r") as f:
                    traversal_data = json.load(f)

                # Determine if run is finished
                actions = traversal_data.get("actions", {})
                has_done = any(
                    action_data.get("action", {}).get("done") is not None
                    for action_data in actions.values()
                )
                current_state = "FINISHED" if has_done else "RUNNING"
                finished_at = (
                    datetime.fromtimestamp(file_stat.st_mtime).isoformat() if has_done else None
                )

                test_description = traversal_data.get("test_case", "")

            except (json.JSONDecodeError, Exception):
                # File being written or corrupted - assume running
                current_state = "RUNNING"
                finished_at = None
                test_description = ""

            return {
                "id": run_id,
                "test_case_id": task_name,
                "test_case_name": task_name,
                "test_description": test_description,
                "current_state": current_state,
                "started_at": started_at,
                "finished_at": finished_at,
                "run_type": "AGENTIC",
                "origin": "WEB_UI",
            }

        except Exception as e:
            print(f"Error creating run summary for {traversal_file}: {e}")
            return None
