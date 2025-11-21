"""Jira integration utilities for Bugninja CLI.

This module provides Jira ticket creation functionality for failed test cases,
including automatic screenshot attachment from previous successful runs.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from jira import JIRA
from jira.exceptions import JIRAError

from bugninja.schemas.pipeline import BugninjaExtendedAction, Traversal
from bugninja.utils.logging_config import logger


class ConfigurationError(Exception):
    """Raised when Jira configuration is invalid.

    This exception is raised when the Jira configuration is present but invalid,
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


class JiraIntegration:
    """Jira integration for creating tickets on test case failures.

    This class handles Jira ticket creation with proper error handling,
    configuration validation, and screenshot attachment from previous runs.

    Attributes:
        server (str): Jira server base URL
        user (str): Jira user email or username
        api_token (str): Jira API token
        project_key (str): Jira project key
        assignees (List[str]): List of assignee usernames
        jira_client (Optional[JIRA]): Jira client instance

    Example:
        ```python
        from bugninja_cli.utils.jira_integration import JiraIntegration

        config = {
            "server": "https://example.atlassian.net",
            "user": "user@example.com",
            "api_token": "token",
            "project_key": "PROJ",
            "assignees": ["user1", "user2"]
        }

        jira = JiraIntegration(config)
        if jira.validate_config():
            ticket_key = jira.create_ticket_for_failure(
                task_name="Login Test",
                failure_step=5,
                error_message="Element not found",
                screenshot_path=Path("./screenshot.png")
            )
        ```
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize Jira integration with configuration.

        Args:
            config (Dict[str, Any]): Jira configuration dictionary containing:
                - server (str): Jira server base URL
                - user (str): Jira user email or username
                - api_token (str): Jira API token
                - project_key (str): Jira project key
                - assignees (List[str], optional): List of assignee usernames
        """
        self.server: Optional[str] = config.get("server")
        self.user: Optional[str] = config.get("user")
        api_token = config.get("api_token")
        if api_token and hasattr(api_token, "get_secret_value"):
            self.api_token: Optional[str] = api_token.get_secret_value()
        else:
            self.api_token = api_token if isinstance(api_token, str) else None
        self.project_key: Optional[str] = config.get("project_key")
        self.assignees: list[str] = config.get("assignees", [])

        self.jira_client: Optional[JIRA] = None

    def validate_config(self) -> bool:
        """Validate Jira configuration.

        Checks if all required fields are present. If config is present but invalid,
        raises ConfigurationError. If config is missing, returns False (allowed).

        Returns:
            bool: True if config is valid, False if config is missing (allowed)

        Raises:
            ConfigurationError: If config is present but invalid
        """
        # If all fields are None/empty, config is missing (allowed)
        if not any([self.server, self.user, self.api_token, self.project_key]):
            return False

        # If some fields are present but not all, config is invalid
        required_fields = {
            "server": self.server,
            "user": self.user,
            "api_token": self.api_token,
            "project_key": self.project_key,
        }

        missing_fields = [field for field, value in required_fields.items() if not value]

        if missing_fields:
            raise ConfigurationError(
                f"Jira configuration is incomplete. Missing fields: {', '.join(missing_fields)}"
            )

        # Test connection (lazy validation)
        try:
            if self.server is None or self.user is None or self.api_token is None:
                raise ConfigurationError("Jira configuration is incomplete")

            self.jira_client = JIRA(server=self.server, basic_auth=(self.user, self.api_token))
            # Test connection by getting current user
            self.jira_client.myself()
            return True
        except JIRAError as e:
            raise ConfigurationError(f"Failed to connect to Jira: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Jira configuration validation failed: {str(e)}")

    def create_ticket_for_failure(
        self,
        task_name: str,
        failure_step: Optional[int] = None,
        error_message: Optional[str] = None,
        screenshot_path: Optional[Path] = None,
        run_type: str = "ai_navigated",
        traversal_path: Optional[Path] = None,
    ) -> Optional[str]:
        """Create a Jira ticket for a failed test case.

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
            Optional[str]: Created ticket key (e.g., "PROJ-123") or None if creation failed
        """
        try:
            if not self.validate_config():
                # Config missing - silently skip (allowed)
                return None

            if not self.jira_client:
                if self.server is None or self.user is None or self.api_token is None:
                    raise ConfigurationError("Jira configuration is incomplete")
                self.jira_client = JIRA(server=self.server, basic_auth=(self.user, self.api_token))

            # Format ticket content
            summary = self._format_ticket_summary(task_name)
            description = self._format_ticket_description(
                task_name, failure_step, error_message, run_type, traversal_path
            )
            comment_text = self._format_comment(failure_step, error_message, traversal_path)

            # Create issue
            issue = self._create_issue(summary, description)

            # Add comment
            if comment_text:
                self._add_comment(issue, comment_text)

            # Attach screenshot if provided
            if screenshot_path and screenshot_path.exists():
                try:
                    self._attach_screenshot(issue, screenshot_path)
                    logger.info(f"📷 Attached screenshot to ticket: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to attach screenshot {screenshot_path}: {str(e)}")

            ticket_key: str = str(issue.key)
            logger.info(f"✅ Created Jira ticket: {ticket_key} for failed test case: {task_name}")
            return ticket_key

        except ConfigurationError:
            # Re-raise configuration errors
            raise
        except Exception as e:
            # Log error but don't block execution
            logger.error(f"Failed to create Jira ticket for '{task_name}': {str(e)}")
            return None

    def _resolve_assignee_identifier(
        self, assignee_email_or_username: str
    ) -> Optional[Dict[str, str]]:
        """Resolve assignee email/username to Jira user identifier.

        For Jira Cloud, uses accountId. For Jira Server, uses username.
        This method handles the conversion from email addresses to the proper
        Jira user identifier required by the API.

        Args:
            assignee_email_or_username (str): Email address or username of the assignee

        Returns:
            Optional[Dict[str, str]]: Dictionary with appropriate identifier key
            ("accountId" for Cloud, "name" for Server) or None if user not found

        Raises:
            ConfigurationError: If Jira client is not initialized
        """
        if not self.jira_client:
            raise ConfigurationError("Jira client not initialized")

        try:
            # Search for user by email or username
            users = self.jira_client.search_users(query=assignee_email_or_username, maxResults=1)

            if not users:
                logger.warning(
                    f"User '{assignee_email_or_username}' not found in Jira. "
                    "Ticket will be created without assignee."
                )
                return None

            user = users[0]

            # Check if this is Jira Cloud (has accountId) or Server (has key/name)
            if hasattr(user, "accountId") and user.accountId:
                # Jira Cloud - use accountId
                return {"accountId": user.accountId}
            elif hasattr(user, "key") and user.key:
                # Jira Server - use key
                return {"name": user.key}
            elif hasattr(user, "name") and user.name:
                # Fallback to name
                return {"name": user.name}
            else:
                logger.warning(
                    f"Could not determine identifier for user '{assignee_email_or_username}'. "
                    "Ticket will be created without assignee."
                )
                return None

        except Exception as e:
            logger.warning(
                f"Failed to resolve assignee '{assignee_email_or_username}': {str(e)}. "
                "Ticket will be created without assignee."
            )
            return None

    def _create_issue(self, summary: str, description: str) -> Any:
        """Create a Jira issue.

        Args:
            summary (str): Issue summary/title
            description (str): Issue description

        Returns:
            Jira issue object
        """
        if not self.jira_client:
            raise ConfigurationError("Jira client not initialized")

        if self.project_key is None:
            raise ConfigurationError("Jira project key is not set")

        issue_dict: Dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Bug"},
        }

        # Add assignees if provided
        if self.assignees:
            assignee_identifier = self._resolve_assignee_identifier(self.assignees[0])
            if assignee_identifier:
                issue_dict["assignee"] = assignee_identifier
            # If resolution fails, issue is created without assignee (logged warning above)

        issue = self.jira_client.create_issue(fields=issue_dict)
        return issue

    def _add_comment(self, issue: Any, comment_text: str) -> None:
        """Add a comment to a Jira issue.

        Args:
            issue: Jira issue object
            comment_text (str): Comment text to add
        """
        if not self.jira_client:
            raise ConfigurationError("Jira client not initialized")

        self.jira_client.add_comment(issue, comment_text)

    def _attach_screenshot(self, issue: Any, screenshot_path: Path) -> None:
        """Attach a screenshot to a Jira issue.

        Args:
            issue: Jira issue object
            screenshot_path (Path): Path to screenshot file
        """
        if not self.jira_client:
            raise ConfigurationError("Jira client not initialized")

        if not screenshot_path.exists():
            raise FileNotFoundError(f"Screenshot file does not exist: {screenshot_path}")

        # Open file in binary mode and pass file object to Jira API
        with open(screenshot_path, "rb") as f:
            self.jira_client.add_attachment(issue=issue, attachment=f)

    def _format_ticket_summary(self, task_name: str) -> str:
        """Format ticket summary/title.

        Args:
            task_name (str): Name of the failing test case

        Returns:
            str: Formatted ticket summary
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
        """Format ticket description with proper Jira markup.

        Args:
            task_name (str): Name of the failing test case
            failure_step (Optional[int]): Step number where failure occurred
            error_message (Optional[str]): Error message
            run_type (str): Type of run
            traversal_path (Optional[Path]): Path to traversal file

        Returns:
            str: Formatted description in Jira markup
        """
        import json
        import re

        description_parts = []

        # Header
        description_parts.append("h2. Test Case Failure Details\n")
        description_parts.append(f"Test case *{task_name}* failed during execution.\n")

        # Failure Information Panel
        description_parts.append(
            "{panel:title=Failure Information|borderStyle=solid|borderColor=#ff5630|titleBGColor=#ff5630|bgColor=#fff4f4}\n"
        )

        if failure_step is not None:
            description_parts.append(f"*Failure Step:* {failure_step}\n")

        description_parts.append(f"*Run Type:* {run_type}\n")

        if traversal_path:
            description_parts.append(f"*Traversal File:* {traversal_path}\n")

        description_parts.append("{panel}\n")

        # Error Message Section
        if error_message:
            description_parts.append("h3. Error Message\n")

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
                        description_parts.append("{code:json}\n")
                        description_parts.append(f"{formatted_json}\n")
                        description_parts.append("{code}\n")
                    except json.JSONDecodeError:
                        # If JSON parsing fails, just add as code block
                        description_parts.append("{code}\n")
                        description_parts.append(f"{json_match}\n")
                        description_parts.append("{code}\n")
            else:
                # No JSON found, just format the error message
                description_parts.append(f"{error_text.strip()}\n")

            # Try to extract error type and details if present
            if "Error Type:" in error_message or "📋 Error Type:" in error_message:
                error_type_match = re.search(r"(?:📋\s*)?Error Type:\s*(\S+)", error_message)
                if error_type_match:
                    error_type = error_type_match.group(1)
                    description_parts.append(f"\n*Error Type:* {error_type}\n")

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
                        description_parts.append("\n*Details:*\n")
                        description_parts.append("{code:json}\n")
                        description_parts.append(f"{formatted_details}\n")
                        description_parts.append("{code}\n")
                    except (json.JSONDecodeError, AttributeError):
                        # Not JSON, just add as code
                        description_parts.append("\n*Details:*\n")
                        description_parts.append("{code}\n")
                        description_parts.append(f"{details_text}\n")
                        description_parts.append("{code}\n")

        return "".join(description_parts)

    def _format_comment(
        self,
        failure_step: Optional[int],
        error_message: Optional[str],
        traversal_path: Optional[Path],
    ) -> str:
        """Format comment text with proper Jira markup.

        Args:
            failure_step (Optional[int]): Step number where failure occurred
            error_message (Optional[str]): Error message
            traversal_path (Optional[Path]): Path to traversal file

        Returns:
            str: Formatted comment text
        """
        comment_parts = []

        if failure_step is not None:
            comment_parts.append(f"Failed at step *{failure_step}*.\n\n")

        if error_message:
            # Extract just the main error message (first line or first sentence)
            main_error = error_message.split("\n")[0].split(".")[0]
            if not main_error.endswith("."):
                main_error += "."
            comment_parts.append(f"*Error:* {main_error}\n")

        if traversal_path:
            comment_parts.append(f"\n*Traversal file:* {traversal_path}")

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

            if not matching_action or not matching_action.screenshot_filename:
                return None

            # Resolve screenshot path
            screenshot_filename = matching_action.screenshot_filename
            screenshot_path = Path(screenshot_filename)

            # If path is absolute, use as-is
            if screenshot_path.is_absolute():
                return screenshot_path if screenshot_path.exists() else None

            # If path is relative, resolve relative to traversal directory
            traversal_dir = previous_successful_traversal_path.parent
            resolved_path = traversal_dir / screenshot_path

            if resolved_path.exists():
                return resolved_path

            # Also try resolving relative to task directory
            if task_info:
                task_dir = task_info.task_path
                task_resolved_path: Path = task_dir / screenshot_path

                if task_resolved_path.exists():
                    return task_resolved_path

            # Try screenshots directory from traversal
            screenshots_dir = traversal_dir / "screenshots"
            screenshots_resolved_path = screenshots_dir / screenshot_path

            if screenshots_resolved_path.exists():
                return screenshots_resolved_path

            # Try just the filename in traversal directory
            filename_only = screenshot_path.name
            filename_resolved = traversal_dir / filename_only

            if filename_resolved.exists():
                return filename_resolved

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
        """Create Jira ticket for failed task execution (shared helper).

        This is a convenience method that extracts failure information and creates
        a Jira ticket. It handles all the common logic for both AI-navigated and replay runs.

        Args:
            task_info: Task information object
            result: TaskExecutionResult object
            run_type (str): Type of run ("ai_navigated" or "replay")
            history_manager: RunHistoryManager instance
            traversal_path_override (Optional[Path]): Override traversal path (for replay)
        """
        try:
            from bugninja.config.factory import ConfigurationFactory

            # Get Jira configuration from settings
            settings = ConfigurationFactory.get_settings(cli_mode=True)

            jira_config = {
                "server": settings.jira_server,
                "user": settings.jira_user,
                "api_token": settings.jira_api_token,
                "project_key": settings.jira_project_key,
                "assignees": settings.jira_assignees,
            }

            # Check if Jira config exists (missing config is allowed)
            jira = JiraIntegration(jira_config)
            if not jira.validate_config():
                # Config missing - silently skip (allowed)
                return

            # Extract failure information
            task_name = task_info.name
            failure_step = None
            error_message = result.error_message

            # Get failure step from result
            if result.result and hasattr(result.result, "steps_completed"):
                failure_step = result.result.steps_completed

            # Get step number from traversal if available
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
                except Exception as e:
                    logger.warning(f"Failed to find traversal file: {str(e)}")

            if traversal_path and traversal_path.exists():
                try:
                    with open(traversal_path, "r", encoding="utf-8") as f:
                        traversal_data = json.load(f)

                    # Find the last action to get step count
                    actions = traversal_data.get("actions", {})
                    if actions:
                        # If failure_step is not set, use the number of actions as the step number
                        # (since the failure happened after the last completed action)
                        if failure_step is None:
                            failure_step = len(actions)
                except Exception as e:
                    logger.warning(f"Failed to extract step info from traversal: {str(e)}")

            # Find screenshot from current failed run's traversal
            screenshot_path = None
            if traversal_path and traversal_path.exists():
                try:
                    with open(traversal_path, "r", encoding="utf-8") as f:
                        traversal_data = json.load(f)

                    # Get the last action from current failed run
                    actions = traversal_data.get("actions", {})
                    if actions:
                        # Get the last action (most recent screenshot)
                        last_action_key = sorted(actions.keys())[-1]
                        last_action = actions[last_action_key]

                        # Get screenshot filename from the last action
                        screenshot_filename = last_action.get("screenshot_filename")

                        if screenshot_filename:
                            # Resolve screenshot path
                            # screenshot_filename format: "screenshots/{run_id}/filename.png"
                            screenshot_path_obj = Path(screenshot_filename)

                            # Try resolving relative to task directory first
                            task_screenshots_path = task_info.task_path / screenshot_path_obj
                            if task_screenshots_path.exists():
                                screenshot_path = task_screenshots_path
                            else:
                                # Try resolving as absolute path (if screenshot_filename is already absolute)
                                if (
                                    screenshot_path_obj.is_absolute()
                                    and screenshot_path_obj.exists()
                                ):
                                    screenshot_path = screenshot_path_obj
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

                                        if potential_path.exists():
                                            screenshot_path = potential_path
                except Exception as e:
                    logger.warning(f"Failed to get screenshot from current failed run: {str(e)}")

            # Create ticket (non-blocking, fire and forget)
            jira.create_ticket_for_failure(
                task_name=task_name,
                failure_step=failure_step,
                error_message=error_message,
                screenshot_path=screenshot_path,
                run_type=run_type,
                traversal_path=traversal_path,
            )

        except Exception as e:
            # Log error but don't block execution
            logger.error(f"Failed to create Jira ticket for '{task_info.name}': {str(e)}")
