"""Redmine integration utilities for Bugninja CLI.

This module provides Redmine ticket creation functionality for failed test cases,
including automatic screenshot attachment from previous successful runs.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, cast

from redminelib import Redmine  # type: ignore
from redminelib.exceptions import ResourceNotFoundError, ValidationError  # type: ignore

from bugninja.schemas.pipeline import BugninjaExtendedAction, Traversal
from bugninja.utils.logging_config import logger


class ConfigurationError(Exception):
    """Raised when Redmine configuration is invalid.

    This exception is raised when the Redmine configuration is present but invalid,
    such as when required fields are missing or connection fails.

    Attributes:
        message (str): Human-readable error message describing the configuration issue
    """

    def __init__(self, message: str) -> None:
        """Initialize ConfigurationError with error message.

        Args:
            message (str): Error message describing the configuration issue
        """
        self.message = message
        super().__init__(self.message)


class RedmineIntegration:
    """Redmine integration for creating tickets on test case failures.

    This class handles Redmine ticket creation with proper error handling,
    configuration validation, and screenshot attachment from previous runs.

    Attributes:
        server (str): Redmine server base URL
        api_key (Optional[str]): Redmine API key (preferred auth method)
        user (Optional[str]): Redmine username (alternative auth)
        password (Optional[str]): Redmine password (alternative auth)
        project_id (str): Redmine project identifier (can be ID or identifier string)
        tracker_id (Optional[int]): Tracker ID for issues (e.g., Bug tracker)
        assignees (List[str]): List of assignee user IDs or usernames
        redmine_client (Optional[Redmine]): Redmine client instance

    Example:
        ```python
        from bugninja_cli.utils.redmine_integration import RedmineIntegration

        config = {
            "server": "https://redmine.example.com",
            "api_key": "token",
            "project_id": "project-identifier",
            "tracker_id": 1,
            "assignees": ["user1", "user2"]
        }

        redmine = RedmineIntegration(config)
        if redmine.validate_config():
            ticket_id = redmine.create_ticket_for_failure(
                task_name="Login Test",
                failure_step=5,
                error_message="Element not found",
                screenshot_path=Path("./screenshot.png")
            )
        ```
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize Redmine integration with configuration.

        Args:
            config (Dict[str, Any]): Redmine configuration dictionary containing:
                - server (str): Redmine server base URL
                - api_key (Optional[str]): Redmine API key (preferred auth method)
                - user (Optional[str]): Redmine username (alternative auth)
                - password (Optional[str]): Redmine password (alternative auth)
                - project_id (str): Redmine project identifier (can be ID or identifier string)
                - tracker_id (Optional[int]): Tracker ID for issues
                - assignees (List[str], optional): List of assignee user IDs or usernames
        """
        self.server: Optional[str] = config.get("server")
        api_key = config.get("api_key")
        if api_key and hasattr(api_key, "get_secret_value"):
            self.api_key: Optional[str] = api_key.get_secret_value()
        else:
            self.api_key = api_key if isinstance(api_key, str) else None
        self.user: Optional[str] = config.get("user")
        password = config.get("password")
        if password and hasattr(password, "get_secret_value"):
            self.password: Optional[str] = password.get_secret_value()
        else:
            self.password = password if isinstance(password, str) else None
        self.project_id: Optional[str] = config.get("project_id")
        tracker_id = config.get("tracker_id")
        self.tracker_id: Optional[int] = int(tracker_id) if tracker_id is not None else None
        self.assignees: list[str] = config.get("assignees", [])

        self.redmine_client: Optional[Redmine] = None

    def validate_config(self) -> bool:
        """Validate Redmine configuration.

        Checks if all required fields are present. If config is present but invalid,
        raises ConfigurationError. If config is missing, returns False (allowed).

        Returns:
            bool: True if config is valid, False if config is missing (allowed)

        Raises:
            ConfigurationError: If config is present but invalid
        """
        # If all fields are None/empty, config is missing (allowed)
        if not any([self.server, self.api_key, self.user, self.project_id]):
            return False

        # Check authentication: need either API key OR (username and password)
        has_api_key = bool(self.api_key)
        has_user_pass = bool(self.user and self.password)

        if not has_api_key and not has_user_pass:
            # Some fields present but no valid auth - config is invalid
            if any([self.server, self.project_id]):
                raise ConfigurationError(
                    "Redmine configuration requires either api_key or (user and password) for authentication"
                )
            return False

        # If some fields are present but not all required ones, config is invalid
        required_fields = {
            "server": self.server,
            "project_id": self.project_id,
        }

        missing_fields = [field for field, value in required_fields.items() if not value]

        if missing_fields:
            raise ConfigurationError(
                f"Redmine configuration is incomplete. Missing fields: {', '.join(missing_fields)}"
            )

        # Test connection (lazy validation)
        try:
            if self.server is None:
                raise ConfigurationError("Redmine server is not set")

            # Initialize client with available auth method
            if self.api_key:
                self.redmine_client = Redmine(url=self.server, key=self.api_key)
            elif self.user and self.password:
                self.redmine_client = Redmine(
                    url=self.server, username=self.user, password=self.password
                )
            else:
                raise ConfigurationError("Redmine authentication not configured")

            # Test connection by trying to access the project
            if self.project_id:
                try:
                    # Try to get the project to verify connection and project access
                    self.redmine_client.project.get(self.project_id)
                except ResourceNotFoundError:
                    raise ConfigurationError(
                        f"Redmine project '{self.project_id}' not found or not accessible"
                    )
            return True
        except (ResourceNotFoundError, ValidationError) as e:
            raise ConfigurationError(f"Failed to connect to Redmine: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Redmine configuration validation failed: {str(e)}")

    def create_ticket_for_failure(
        self,
        task_name: str,
        failure_step: Optional[int] = None,
        error_message: Optional[str] = None,
        screenshot_path: Optional[Path] = None,
        run_type: str = "ai_navigated",
        traversal_path: Optional[Path] = None,
    ) -> Optional[str]:
        """Create a Redmine ticket for a failed test case.

        This method creates a ticket non-blocking (fire and forget) with proper
        error handling. Errors are logged but don't raise exceptions.

        Args:
            task_name (str): Name of the failing test case
            failure_step (Optional[int]): Step number where failure occurred
            error_message (Optional[str]): Error message or failure reason
            screenshot_path (Optional[Path]): Path to screenshot to attach
            run_type (str): Type of run ("ai_navigated" or "replay")
            traversal_path (Optional[Path]): Path to traversal file for reference

        Returns:
            Optional[str]: Created ticket ID (e.g., "12345") or None if creation failed
        """
        try:
            if not self.validate_config():
                # Config missing - silently skip (allowed)
                return None

            if not self.redmine_client:
                if self.server is None:
                    raise ConfigurationError("Redmine server is not set")
                # Reinitialize client
                if self.api_key:
                    self.redmine_client = Redmine(url=self.server, key=self.api_key)
                elif self.user and self.password:
                    self.redmine_client = Redmine(
                        url=self.server, username=self.user, password=self.password
                    )
                else:
                    raise ConfigurationError("Redmine authentication not configured")

            # Format ticket content
            subject = self._format_ticket_summary(task_name)
            description = self._format_ticket_description(
                task_name, failure_step, error_message, run_type, traversal_path
            )
            notes_text = self._format_comment(failure_step, error_message, traversal_path)

            # Prepare uploads for screenshot if provided
            uploads = []
            if screenshot_path and screenshot_path.exists():
                try:
                    uploads.append({"path": str(screenshot_path)})
                except Exception as e:
                    logger.warning(f"Failed to prepare screenshot for upload: {str(e)}")

            # Create issue
            issue = self._create_issue(subject, description, uploads)

            # Add comment/notes if provided
            if notes_text:
                self._add_comment(issue, notes_text)

            # If screenshot wasn't attached during creation, try to attach it now
            if screenshot_path and screenshot_path.exists() and not uploads:
                try:
                    self._attach_screenshot(issue, screenshot_path)
                    logger.info(f"📷 Attached screenshot to ticket: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to attach screenshot {screenshot_path}: {str(e)}")

            ticket_id: str = str(issue.id)
            logger.info(
                f"✅ Created Redmine ticket: #{ticket_id} for failed test case: {task_name}"
            )
            return ticket_id

        except ConfigurationError:
            # Re-raise configuration errors
            raise
        except Exception as e:
            # Log error but don't block execution
            logger.error(f"Failed to create Redmine ticket for '{task_name}': {str(e)}")
            return None

    def _resolve_assignee_identifier(self, assignee_username_or_id: str) -> Optional[int]:
        """Resolve assignee username/ID to Redmine user ID.

        This method handles the conversion from usernames or user IDs to the proper
        Redmine user ID required by the API.

        Args:
            assignee_username_or_id (str): Username or user ID of the assignee

        Returns:
            Optional[int]: Redmine user ID or None if user not found

        Raises:
            ConfigurationError: If Redmine client is not initialized
        """
        if not self.redmine_client:
            raise ConfigurationError("Redmine client not initialized")

        try:
            # Try to parse as integer ID first
            try:
                user_id = int(assignee_username_or_id)
                # Verify user exists
                user = self.redmine_client.user.get(user_id)
                return cast(int, user.id)
            except (ValueError, ResourceNotFoundError):
                # Not an integer ID, try to find by username/login
                pass

            # Search for user by username/login
            try:
                # Try to get user by login/username
                users = self.redmine_client.user.filter(name=assignee_username_or_id)
                if users:
                    return cast(int, users[0].id)

                # Try alternative search methods
                # Note: python-redmine may have different methods depending on version
                # Try getting all users and filtering (less efficient but more compatible)
                all_users = self.redmine_client.user.all()
                for user in all_users:
                    if (
                        hasattr(user, "login")
                        and user.login == assignee_username_or_id
                        or (hasattr(user, "name") and user.name == assignee_username_or_id)
                    ):
                        return cast(int, user.id)

                logger.warning(
                    f"User '{assignee_username_or_id}' not found in Redmine. "
                    "Ticket will be created without assignee."
                )
                return None
            except Exception:
                logger.warning(
                    f"Failed to search for user '{assignee_username_or_id}'. "
                    "Ticket will be created without assignee."
                )
                return None

        except Exception as e:
            logger.warning(
                f"Failed to resolve assignee '{assignee_username_or_id}': {str(e)}. "
                "Ticket will be created without assignee."
            )
            return None

    def _create_issue(
        self,
        subject: str,
        description: str,
        uploads: Optional[list[Dict[str, Any]]] = None,
    ) -> Any:
        """Create a Redmine issue.

        Args:
            subject (str): Issue subject/title
            description (str): Issue description
            uploads (Optional[list]): List of upload dictionaries with file paths

        Returns:
            Redmine issue object
        """
        if not self.redmine_client:
            raise ConfigurationError("Redmine client not initialized")

        if self.project_id is None:
            raise ConfigurationError("Redmine project ID is not set")

        # Prepare issue creation parameters
        issue_params: Dict[str, Any] = {
            "project_id": self.project_id,
            "subject": subject,
            "description": description,
        }

        # Add tracker ID if provided
        if self.tracker_id is not None:
            issue_params["tracker_id"] = self.tracker_id

        # Add assignees if provided
        if self.assignees:
            assignee_id = self._resolve_assignee_identifier(self.assignees[0])
            if assignee_id:
                issue_params["assigned_to_id"] = assignee_id
            # If resolution fails, issue is created without assignee (logged warning above)

        # Add uploads if provided
        if uploads:
            issue_params["uploads"] = uploads

        try:
            issue = self.redmine_client.issue.create(**issue_params)
            return issue
        except (ResourceNotFoundError, ValidationError) as e:
            raise ConfigurationError(f"Failed to create Redmine issue: {str(e)}")

    def _add_comment(self, issue: Any, notes_text: str) -> None:
        """Add a comment/notes to a Redmine issue.

        Args:
            issue: Redmine issue object
            notes_text (str): Comment/notes text to add
        """
        if not self.redmine_client:
            raise ConfigurationError("Redmine client not initialized")

        try:
            # Update issue with notes
            issue.notes = notes_text
            issue.save()
        except Exception as e:
            logger.warning(f"Failed to add comment to Redmine issue: {str(e)}")

    def _attach_screenshot(self, issue: Any, screenshot_path: Path) -> None:
        """Attach a screenshot to a Redmine issue.

        Args:
            issue: Redmine issue object
            screenshot_path (Path): Path to screenshot file
        """
        if not self.redmine_client:
            raise ConfigurationError("Redmine client not initialized")

        if not screenshot_path.exists():
            raise FileNotFoundError(f"Screenshot file does not exist: {screenshot_path}")

        try:
            # Add attachment by updating issue with uploads
            issue.uploads = [{"path": str(screenshot_path)}]
            issue.save()
        except Exception as e:
            logger.warning(f"Failed to attach screenshot to Redmine issue: {str(e)}")
            raise

    def _format_ticket_summary(self, task_name: str) -> str:
        """Format ticket subject/title.

        Args:
            task_name (str): Name of the failing test case

        Returns:
            str: Formatted ticket subject
        """
        return f"Testcase failing {task_name}"

    def _format_ticket_description(
        self,
        task_name: str,
        failure_step: Optional[int],
        error_message: Optional[str],
        run_type: str,
        traversal_path: Optional[Path],
    ) -> str:
        """Format ticket description with Markdown formatting.

        Args:
            task_name (str): Name of the failing test case
            failure_step (Optional[int]): Step number where failure occurred
            error_message (Optional[str]): Error message
            run_type (str): Type of run
            traversal_path (Optional[Path]): Path to traversal file

        Returns:
            str: Formatted description in Markdown
        """
        import re

        description_parts = []

        # Header
        description_parts.append("## Test Case Failure Details\n\n")
        description_parts.append(f"Test case **{task_name}** failed during execution.\n\n")

        # Failure Information Section
        description_parts.append("### Failure Information\n\n")

        if failure_step is not None:
            description_parts.append(f"**Failure Step:** {failure_step}\n\n")

        description_parts.append(f"**Run Type:** {run_type}\n\n")

        if traversal_path:
            description_parts.append(f"**Traversal File:** `{traversal_path}`\n\n")

        # Error Message Section
        if error_message:
            description_parts.append("### Error Message\n\n")

            # Try to extract JSON from error message and format it separately
            error_text = error_message

            # Look for JSON-like structures in the error message (simple pattern)
            json_pattern = r'(\{[^{}]*"agent_state"[^{}]*\})'
            json_matches = re.findall(json_pattern, error_text)

            # Also look for more complex JSON structures
            if not json_matches:
                # Try to find any JSON object in the message
                json_pattern = r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})"
                json_matches = re.findall(json_pattern, error_text)

            if json_matches:
                # Remove JSON from main error text
                for match in json_matches:
                    error_text = error_text.replace(match, "").strip()

                # Format main error message
                if error_text:
                    description_parts.append(f"{error_text}\n\n")

                # Add formatted JSON in code block
                for json_match in json_matches:
                    try:
                        json_obj = json.loads(json_match)
                        formatted_json = json.dumps(json_obj, indent=2)
                        description_parts.append("```json\n")
                        description_parts.append(f"{formatted_json}\n")
                        description_parts.append("```\n\n")
                    except json.JSONDecodeError:
                        # If JSON parsing fails, just add as code block
                        description_parts.append("```\n")
                        description_parts.append(f"{json_match}\n")
                        description_parts.append("```\n\n")
            else:
                # No JSON found, just format the error message
                description_parts.append(f"{error_text.strip()}\n\n")

            # Try to extract error type and details if present
            if "Error Type:" in error_message or "📋 Error Type:" in error_message:
                error_type_match = re.search(r"(?:📋\s*)?Error Type:\s*(\S+)", error_message)
                if error_type_match:
                    error_type = error_type_match.group(1)
                    description_parts.append(f"**Error Type:** {error_type}\n\n")

            if "Details:" in error_message or "📝 Details:" in error_message:
                # Extract details section
                details_match = re.search(
                    r"(?:📝\s*)?Details:\s*(.*?)(?:\n(?:🔍|💡|\*)|$)", error_message, re.DOTALL
                )
                if details_match:
                    details_text = details_match.group(1).strip()
                    # Try to parse as JSON
                    try:
                        details_json = json.loads(details_text)
                        formatted_details = json.dumps(details_json, indent=2)
                        description_parts.append("**Details:**\n\n")
                        description_parts.append("```json\n")
                        description_parts.append(f"{formatted_details}\n")
                        description_parts.append("```\n\n")
                    except (json.JSONDecodeError, AttributeError):
                        # Not JSON, just add as code
                        description_parts.append("**Details:**\n\n")
                        description_parts.append("```\n")
                        description_parts.append(f"{details_text}\n")
                        description_parts.append("```\n\n")

        return "".join(description_parts)

    def _format_comment(
        self,
        failure_step: Optional[int],
        error_message: Optional[str],
        traversal_path: Optional[Path],
    ) -> str:
        """Format comment/notes text with Markdown formatting.

        Args:
            failure_step (Optional[int]): Step number where failure occurred
            error_message (Optional[str]): Error message
            traversal_path (Optional[Path]): Path to traversal file

        Returns:
            str: Formatted comment text in Markdown
        """
        comment_parts = []

        if failure_step is not None:
            comment_parts.append(f"Failed at step **{failure_step}**.\n\n")

        if error_message:
            # Extract just the main error message (first line or first sentence)
            main_error = error_message.split("\n")[0].split(".")[0]
            if not main_error.endswith("."):
                main_error += "."
            comment_parts.append(f"**Error:** {main_error}\n\n")

        if traversal_path:
            comment_parts.append(f"**Traversal file:** `{traversal_path}`")

        return "".join(comment_parts) if comment_parts else ""

    @staticmethod
    def find_screenshot_for_failing_step(
        task_info: Any,
        failed_action_index: int,
        previous_successful_traversal_path: Optional[Path],
    ) -> Optional[Path]:
        """Find screenshot from previous successful run matching the failing step.

        Args:
            task_info: Task information object
            failed_action_index (int): Index of the failed action (idx_in_brainstate)
            previous_successful_traversal_path (Optional[Path]): Path to previous successful traversal

        Returns:
            Optional[Path]: Path to matching screenshot, or None if not found
        """
        if (
            not previous_successful_traversal_path
            or not previous_successful_traversal_path.exists()
        ):
            logger.bugninja_log("No previous successful traversal found for screenshot lookup")
            return None

        try:
            # Load traversal JSON
            with open(previous_successful_traversal_path, "r", encoding="utf-8") as f:
                traversal_data = json.load(f)

            # Parse as Traversal model
            traversal = Traversal.model_validate(traversal_data)

            # Find action with matching idx_in_brainstate
            matching_action: Optional[BugninjaExtendedAction] = None
            for action in traversal.actions.values():
                if action.idx_in_brainstate == failed_action_index:
                    matching_action = action
                    break

            # If exact match not found, find closest match
            if not matching_action:
                closest_action: Optional[BugninjaExtendedAction] = None
                min_diff = float("inf")
                for action in traversal.actions.values():
                    diff = abs(action.idx_in_brainstate - failed_action_index)
                    if diff < min_diff:
                        min_diff = diff
                        closest_action = action

                matching_action = closest_action

            if not matching_action:
                logger.bugninja_log(f"No matching action found for index {failed_action_index}")
                return None

            if not matching_action.screenshot_filename:
                logger.bugninja_log(
                    f"Action at index {failed_action_index} has no screenshot_filename"
                )
                return None

            # Resolve screenshot path
            screenshot_filename = matching_action.screenshot_filename
            logger.bugninja_log(f"Found screenshot_filename: {screenshot_filename}")
            screenshot_path = Path(screenshot_filename)

            # If path is absolute, use as-is
            if screenshot_path.is_absolute():
                if screenshot_path.exists():
                    logger.bugninja_log(f"Using absolute screenshot path: {screenshot_path}")
                    return screenshot_path
                logger.bugninja_log(f"Absolute screenshot path does not exist: {screenshot_path}")
                return None

            # If path is relative, resolve relative to traversal directory
            traversal_dir = previous_successful_traversal_path.parent
            resolved_path = traversal_dir / screenshot_path
            logger.bugninja_log(f"Trying screenshot path relative to traversal: {resolved_path}")

            if resolved_path.exists():
                logger.bugninja_log(f"Found screenshot at: {resolved_path}")
                return resolved_path

            # Also try resolving relative to task directory
            if task_info:
                task_dir = task_info.task_path
                task_resolved_path: Path = task_dir / screenshot_path
                logger.bugninja_log(
                    f"Trying screenshot path relative to task: {task_resolved_path}"
                )

                if task_resolved_path.exists():
                    logger.bugninja_log(f"Found screenshot at: {task_resolved_path}")
                    return task_resolved_path

            # Try screenshots directory from traversal
            screenshots_dir = traversal_dir / "screenshots"
            screenshots_resolved_path = screenshots_dir / screenshot_path
            logger.bugninja_log(
                f"Trying screenshot path in screenshots dir: {screenshots_resolved_path}"
            )

            if screenshots_resolved_path.exists():
                logger.bugninja_log(f"Found screenshot at: {screenshots_resolved_path}")
                return screenshots_resolved_path

            # Try just the filename in traversal directory
            filename_only = screenshot_path.name
            filename_resolved = traversal_dir / filename_only
            logger.bugninja_log(f"Trying screenshot filename only: {filename_resolved}")

            if filename_resolved.exists():
                logger.bugninja_log(f"Found screenshot at: {filename_resolved}")
                return filename_resolved

            logger.bugninja_log("Could not find screenshot at any of the tried paths")
            return None

        except Exception as e:
            logger.warning(f"Failed to find screenshot for failing step: {str(e)}")
            return None

    @staticmethod
    def create_ticket_for_task_failure(
        task_info: Any,
        result: Any,
        run_type: str,
        history_manager: Any,
        traversal_path_override: Optional[Path] = None,
    ) -> None:
        """Create Redmine ticket for failed task execution (shared helper).

        This is a convenience method that extracts failure information and creates
        a Redmine ticket. It handles all the common logic for both AI-navigated and replay runs.

        Args:
            task_info: Task information object
            result: TaskExecutionResult object
            run_type (str): Type of run ("ai_navigated" or "replay")
            history_manager: RunHistoryManager instance
            traversal_path_override (Optional[Path]): Override traversal path (for replay)
        """
        try:
            from bugninja.config.factory import ConfigurationFactory

            # Get Redmine configuration from settings
            settings = ConfigurationFactory.get_settings(cli_mode=True)

            redmine_config = {
                "server": settings.redmine_server,
                "api_key": settings.redmine_api_key,
                "user": settings.redmine_user,
                "password": settings.redmine_password,
                "project_id": settings.redmine_project_id,
                "tracker_id": settings.redmine_tracker_id,
                "assignees": settings.redmine_assignees,
            }

            # Check if Redmine config exists (missing config is allowed)
            redmine = RedmineIntegration(redmine_config)
            if not redmine.validate_config():
                # Config missing - silently skip (allowed)
                return

            # Extract failure information
            task_name = task_info.name
            failure_step = None
            error_message = result.error_message

            # Get failure step from result
            if result.result and hasattr(result.result, "steps_completed"):
                failure_step = result.result.steps_completed

            # Get action index and step number from traversal if available
            failed_action_index = None
            traversal_path = traversal_path_override or result.traversal_path

            # If traversal_path is None, try to find the most recent traversal file
            if not traversal_path:
                try:
                    traversals_dir = task_info.task_path / "traversals"
                    if traversals_dir.exists():
                        traversal_files = list(traversals_dir.glob("*.json"))
                        if traversal_files:
                            # Get the most recent file
                            traversal_path = max(traversal_files, key=lambda f: f.stat().st_mtime)
                            logger.bugninja_log(
                                f"📂 Found most recent traversal file: {traversal_path}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to find traversal file: {str(e)}")

            if traversal_path and traversal_path.exists():
                try:
                    with open(traversal_path, "r", encoding="utf-8") as f:
                        traversal_data = json.load(f)

                    # Find the last action to get its index
                    actions = traversal_data.get("actions", {})
                    if actions:
                        # Get the last action
                        last_action_key = sorted(actions.keys())[-1]
                        last_action = actions[last_action_key]
                        failed_action_index = last_action.get("idx_in_brainstate")

                        # If failure_step is not set, use the number of actions as the step number
                        # (since the failure happened after the last completed action)
                        if failure_step is None:
                            failure_step = len(actions)

                        logger.bugninja_log(
                            f"Extracted failure_step: {failure_step}, failed_action_index: {failed_action_index}, "
                            f"total_actions: {len(actions)}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to extract step info from traversal: {str(e)}")

            # Find screenshot from current failed run's traversal
            screenshot_path = None
            logger.bugninja_log(
                f"🔍 Looking for screenshot - traversal_path: {traversal_path}, exists: {traversal_path.exists() if traversal_path else False}"
            )
            if traversal_path and traversal_path.exists():
                try:
                    logger.bugninja_log(f"📂 Reading traversal file: {traversal_path}")
                    with open(traversal_path, "r", encoding="utf-8") as f:
                        traversal_data = json.load(f)

                    # Get the last action from current failed run
                    actions = traversal_data.get("actions", {})
                    logger.bugninja_log(f"📋 Found {len(actions)} actions in traversal")
                    if actions:
                        # Get the last action (most recent screenshot)
                        last_action_key = sorted(actions.keys())[-1]
                        last_action = actions[last_action_key]
                        logger.bugninja_log(f"🎯 Last action key: {last_action_key}")

                        # Get screenshot filename from the last action
                        screenshot_filename = last_action.get("screenshot_filename")
                        logger.bugninja_log(
                            f"📸 Screenshot filename from last action: {screenshot_filename}"
                        )

                        if screenshot_filename:
                            logger.bugninja_log(
                                f"Found screenshot_filename in last action: {screenshot_filename}"
                            )

                            # Resolve screenshot path
                            # screenshot_filename format: "screenshots/{run_id}/filename.png"
                            screenshot_path_obj = Path(screenshot_filename)

                            # Try resolving relative to task directory first
                            task_screenshots_path = task_info.task_path / screenshot_path_obj
                            logger.bugninja_log(
                                f"🔍 Trying task-relative path: {task_screenshots_path} (exists: {task_screenshots_path.exists()})"
                            )
                            if task_screenshots_path.exists():
                                screenshot_path = task_screenshots_path
                                logger.bugninja_log(f"✅ Found screenshot at: {screenshot_path}")
                            else:
                                # Try resolving as absolute path (if screenshot_filename is already absolute)
                                if (
                                    screenshot_path_obj.is_absolute()
                                    and screenshot_path_obj.exists()
                                ):
                                    screenshot_path = screenshot_path_obj
                                    logger.bugninja_log(
                                        f"Found screenshot at absolute path: {screenshot_path}"
                                    )
                                else:
                                    # Try extracting run_id and looking in screenshots directory
                                    # Format: screenshots/{run_id}/filename.png
                                    parts = screenshot_path_obj.parts
                                    if len(parts) >= 3 and parts[0] == "screenshots":
                                        run_id = parts[1]
                                        filename = parts[2]
                                        screenshots_dir = (
                                            task_info.task_path / "screenshots" / run_id
                                        )
                                        potential_path = screenshots_dir / filename

                                        logger.bugninja_log(
                                            f"Trying screenshot path: {potential_path}"
                                        )
                                        if potential_path.exists():
                                            screenshot_path = potential_path
                                            logger.bugninja_log(
                                                f"Found screenshot at: {screenshot_path}"
                                            )
                                        else:
                                            logger.bugninja_log(
                                                f"Screenshot not found at: {potential_path}"
                                            )
                                    else:
                                        logger.bugninja_log(
                                            f"Could not parse screenshot path structure: {screenshot_filename}"
                                        )
                        else:
                            logger.bugninja_log("⚠️ Last action has no screenshot_filename")
                    else:
                        logger.bugninja_log("⚠️ No actions found in traversal")
                except Exception as e:
                    logger.warning(
                        f"Failed to get screenshot from current failed run: {str(e)}",
                        exc_info=True,
                    )
            else:
                logger.bugninja_log(
                    f"⚠️ Traversal path not available or doesn't exist: {traversal_path}"
                )

            # Create ticket (non-blocking, fire and forget)
            redmine.create_ticket_for_failure(
                task_name=task_name,
                failure_step=failure_step,
                error_message=error_message,
                screenshot_path=screenshot_path,
                run_type=run_type,
                traversal_path=traversal_path,
            )

        except Exception as e:
            # Log error but don't block execution
            logger.error(f"Failed to create Redmine ticket for '{task_info.name}': {str(e)}")
