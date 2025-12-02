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

        Also checks run_history.json for replay runs that don't have traversal files.

        Args:
            run_id (str): Run identifier

        Returns:
            Optional[Dict]: Run details in frontend format, or None if not found
        """
        # First, try to find traversal file (for AI runs)
        traversal_file = self.find_traversal_file(run_id)

        if traversal_file and traversal_file.exists():
            # Read and transform traversal file - ALWAYS read fresh from disk
            try:
                with open(traversal_file, "r") as f:
                    traversal_data = json.load(f)

                return self._transform_traversal_to_run(traversal_data, run_id, traversal_file)

            except (json.JSONDecodeError, Exception) as e:
                # File is being written (partial JSON) - return RUNNING state
                print(f"Error reading traversal file (likely being written): {e}")
                return self._create_running_response(run_id)

        # No traversal file found - check for replay run in run_history.json
        replay_run = self._find_replay_run_by_id(run_id)
        if replay_run:
            return replay_run

        # Nothing found - return RUNNING state (might be a new run starting up)
        return self._create_running_response(run_id)

    def _find_replay_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Find a replay run by ID from run_history.json files.

        Args:
            run_id (str): Run identifier to search for

        Returns:
            Optional[Dict]: Replay run details or None if not found
        """
        if not self.tasks_dir.exists():
            return None

        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            run_history_path = task_dir / "run_history.json"
            if not run_history_path.exists():
                continue

            try:
                with open(run_history_path, "r") as f:
                    history_data = json.load(f)

                replay_runs = history_data.get("replay_runs", [])
                for replay_run in replay_runs:
                    if replay_run.get("run_id") == run_id:
                        return self._transform_replay_run_to_details(
                            replay_run, task_dir.name, task_dir
                        )

            except (json.JSONDecodeError, Exception):
                continue

        return None

    def _transform_replay_run_to_details(
        self, replay_run: Dict[str, Any], task_name: str, task_dir: Path
    ) -> Dict[str, Any]:
        """Transform a replay run entry to the full details format.

        Args:
            replay_run (Dict): Replay run data from run_history.json
            task_name (str): Name of the task
            task_dir (Path): Path to the task directory

        Returns:
            Dict: Run details in frontend format
        """
        run_id = replay_run.get("run_id", "")
        
        # Map status to current_state
        status = replay_run.get("status", "")
        if status in ("successful", "success"):
            current_state = "FINISHED"
        elif status == "failed":
            current_state = "FAILED"
        elif status == "pending":
            current_state = "RUNNING"
        else:
            current_state = "UNKNOWN"

        timestamp = replay_run.get("timestamp", "")
        finished_at = timestamp if current_state in ("FINISHED", "FAILED") else None

        # Read task TOML for description
        toml_data = self._read_task_toml(task_dir)
        test_goal = ""
        if toml_data:
            test_goal = toml_data.get("task", {}).get("description", "")

        return {
            "id": run_id,
            "test_case": {
                "id": task_name,
                "test_name": task_name,
                "test_description": test_goal,
                "test_goal": test_goal,
            },
            "current_state": current_state,
            "started_at": timestamp,
            "finished_at": finished_at,
            "run_type": "REPLAY",
            "origin": "WEB_UI",
            "healing_enabled": replay_run.get("healing_enabled", False),
            "original_run_id": replay_run.get("original_traversal_id"),
            "execution_time": replay_run.get("execution_time", 0),
            "error_message": replay_run.get("error_message"),
            "browser_config": None,
            "brain_states": [],  # Replay runs don't have brain states stored
            "run_gif": None,
            "test_traversal_id": run_id,
        }

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

        # Get run_type from traversal data (REPLAY or AGENTIC), default to AGENTIC for backwards compatibility
        run_type = traversal_data.get("run_type", "AGENTIC")
        
        # For REPLAY runs, also check status field for completion
        traversal_status = traversal_data.get("status", "")
        if run_type == "REPLAY":
            if traversal_status == "SUCCESSFUL":
                current_state = "FINISHED"
            elif traversal_status == "FAILED":
                current_state = "FAILED"
            # else keep the current_state from done action check

        return {
            "id": run_id,
            "test_case": test_case,
            "current_state": current_state,
            "started_at": started_at,
            "finished_at": finished_at,
            "run_type": run_type,
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

        For REPLAY runs (which have empty brain_states), generates synthetic
        brain states from actions so the frontend can display execution steps.

        Args:
            traversal_data (Dict): Parsed traversal JSON
            task_name (str): Name of the task (for screenshot URLs)

        Returns:
            List[Dict]: Transformed brain states with history elements
        """
        brain_states_dict = traversal_data.get("brain_states", {})
        actions_dict = traversal_data.get("actions", {})
        run_type = traversal_data.get("run_type", "AGENTIC")

        # Group actions by brain_state_id
        actions_by_brain_state: Dict[str, List[Dict[str, Any]]] = {}
        for action_key, action_data in actions_dict.items():
            brain_state_id = action_data.get("brain_state_id")
            if brain_state_id:
                if brain_state_id not in actions_by_brain_state:
                    actions_by_brain_state[brain_state_id] = []
                actions_by_brain_state[brain_state_id].append(action_data)

        # For REPLAY runs with no brain_states, generate synthetic ones from actions
        if not brain_states_dict and actions_dict and run_type == "REPLAY":
            return self._generate_synthetic_brain_states(actions_dict, task_name)

        # Transform brain states (normal AGENTIC flow)
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

    def _generate_synthetic_brain_states(
        self, actions_dict: Dict[str, Any], task_name: str
    ) -> List[Dict[str, Any]]:
        """Generate synthetic brain states from actions for REPLAY runs.

        Since replay runs don't have AI reasoning, we create one brain state
        per action to display the execution steps in the frontend.

        Args:
            actions_dict (Dict): Actions from the traversal
            task_name (str): Name of the task (for screenshot URLs)

        Returns:
            List[Dict]: Synthetic brain states with one action each
        """
        brain_states = []
        
        # Sort actions by key (action_0, action_1, etc.)
        sorted_actions = sorted(actions_dict.items(), key=lambda x: int(x[0].split("_")[1]) if "_" in x[0] else 0)
        
        for idx, (action_key, action_data) in enumerate(sorted_actions):
            # Get the action type for display
            action_raw = action_data.get("action", {})
            action_type = "Unknown action"
            action_detail = ""
            
            for act_type, act_value in action_raw.items():
                if act_value is not None:
                    action_type = act_type.replace("_", " ").title()
                    # Get detail based on action type
                    if isinstance(act_value, dict):
                        if "text" in act_value:
                            action_detail = f": '{act_value['text'][:30]}...'" if len(act_value.get('text', '')) > 30 else f": '{act_value.get('text', '')}'"
                        elif "url" in act_value:
                            action_detail = f": {act_value['url']}"
                    break
            
            # Transform action to history element
            history_element = self._transform_action_to_history_element(
                action_data, 0, task_name
            )
            
            # Create synthetic brain state
            brain_state = {
                "id": f"replay_step_{idx}",
                "evaluation_previous_goal": "Success" if idx > 0 else "Starting replay",
                "next_goal": f"Step {idx + 1}: {action_type}{action_detail}",
                "memory": f"Replaying recorded action {idx + 1} of {len(actions_dict)}",
                "history_elements": [history_element],
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

        # Process traversal files (both AI runs and REPLAY runs)
        traversals_dir = task_dir / "traversals"
        seen_run_ids = set()
        
        if traversals_dir.exists():
            for traversal_file in traversals_dir.glob("*.json"):
                run_summary = self._create_run_summary(traversal_file, task_dir.name)
                if run_summary:
                    run_id = run_summary.get("id")
                    if run_id and run_id not in seen_run_ids:
                        runs.append(run_summary)
                        seen_run_ids.add(run_id)

        # Process replay runs from run_history.json (only add if not already seen from traversal)
        replay_runs = self._get_replay_runs_from_history(task_dir)
        for replay_run in replay_runs:
            run_id = replay_run.get("id")
            if run_id and run_id not in seen_run_ids:
                runs.append(replay_run)
                seen_run_ids.add(run_id)

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
            run_type = "AGENTIC"  # Default
            try:
                with open(traversal_file, "r") as f:
                    traversal_data = json.load(f)

                # Get run_type from traversal data
                run_type = traversal_data.get("run_type", "AGENTIC")
                
                # Determine if run is finished
                actions = traversal_data.get("actions", {})
                has_done = any(
                    action_data.get("action", {}).get("done") is not None
                    for action_data in actions.values()
                )
                current_state = "FINISHED" if has_done else "RUNNING"
                
                # For REPLAY runs, check status field
                if run_type == "REPLAY":
                    traversal_status = traversal_data.get("status", "")
                    if traversal_status == "SUCCESSFUL":
                        current_state = "FINISHED"
                    elif traversal_status == "FAILED":
                        current_state = "FAILED"
                
                finished_at = (
                    datetime.fromtimestamp(file_stat.st_mtime).isoformat() 
                    if current_state in ("FINISHED", "FAILED") else None
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
                "run_type": run_type,
                "origin": "WEB_UI",
            }

        except Exception as e:
            print(f"Error creating run summary for {traversal_file}: {e}")
            return None

    def _get_replay_runs_from_history(self, task_dir: Path) -> List[Dict[str, Any]]:
        """Get replay runs from run_history.json.

        Args:
            task_dir (Path): Path to the task directory

        Returns:
            List[Dict]: List of replay run summaries
        """
        runs = []
        run_history_path = task_dir / "run_history.json"
        
        if not run_history_path.exists():
            return runs
        
        try:
            with open(run_history_path, "r") as f:
                history_data = json.load(f)
            
            replay_runs = history_data.get("replay_runs", [])
            task_name = task_dir.name
            
            for replay_run in replay_runs:
                run_summary = self._create_replay_run_summary(replay_run, task_name)
                if run_summary:
                    runs.append(run_summary)
                    
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error reading run_history.json from {task_dir}: {e}")
        
        return runs

    def _create_replay_run_summary(
        self, replay_run: Dict[str, Any], task_name: str
    ) -> Optional[Dict[str, Any]]:
        """Create a run summary from a replay run entry.

        Args:
            replay_run (Dict): Replay run data from run_history.json
            task_name (str): Name of the task

        Returns:
            Optional[Dict]: Run summary or None if data is invalid
        """
        try:
            run_id = replay_run.get("run_id")
            if not run_id:
                return None
            
            # Map status to current_state
            status = replay_run.get("status", "")
            if status in ("successful", "success"):
                current_state = "FINISHED"
            elif status == "failed":
                current_state = "FAILED"
            elif status == "pending":
                current_state = "RUNNING"
            else:
                current_state = "UNKNOWN"
            
            # Parse timestamp
            timestamp = replay_run.get("timestamp", "")
            started_at = timestamp if timestamp else None
            
            # For finished runs, use timestamp as finished_at too
            finished_at = timestamp if current_state in ("FINISHED", "FAILED") else None
            
            return {
                "id": run_id,
                "test_case_id": task_name,
                "test_case_name": task_name,
                "test_description": f"Replay of {replay_run.get('original_traversal_id', 'unknown')}",
                "current_state": current_state,
                "started_at": started_at,
                "finished_at": finished_at,
                "run_type": "REPLAY",
                "origin": "WEB_UI",
                "healing_enabled": replay_run.get("healing_enabled", False),
                "original_traversal_id": replay_run.get("original_traversal_id"),
                "execution_time": replay_run.get("execution_time", 0),
                "error_message": replay_run.get("error_message"),
            }
            
        except Exception as e:
            print(f"Error creating replay run summary: {e}")
            return None
