"""
Retention policy management for Bugninja CLI.

This module provides comprehensive retention policy management for testcase-related
media files (videos, screenshots) and traversal files based on configurable rules
including age-based deletion, maximum run limits, and per-testcase retention.
"""

import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetentionPolicyConfig(BaseModel):
    """Configuration for retention policy system.

    This class defines the rules for cleaning up testcase-related media files
    (videos, screenshots) and traversal files based on simplified retention rules:
    1. Keep runs younger than max_age_days (default: 14 days)
    2. Always keep the last N runs regardless of age (default: 2)

    Attributes:
        max_age_days (int): Maximum age in days - runs older than this are deleted (default: 14)
        keep_last_runs (int): Number of most recent runs to always keep per testcase per run type (default: 2)
        cleanup_traversals (bool): Whether to include traversal files in cleanup (default: True)
    """

    max_age_days: int = Field(
        default=14,
        description="Maximum age in days - runs older than this are deleted (default: 14)",
    )
    keep_last_runs: int = Field(
        default=2,
        description="Number of most recent runs to always keep per testcase per run type (default: 2)",
    )
    cleanup_traversals: bool = Field(
        default=True, description="Whether to include traversal files in cleanup (default: True)"
    )


@dataclass
class MediaFiles:
    """Container for media files associated with a run."""

    video_file: Optional[Path] = None
    screenshot_dir: Optional[Path] = None
    traversal_file: Optional[Path] = None


@dataclass
class TaskCleanupResult:
    """Result of cleanup operation for a single task."""

    task_name: str
    deleted_ai_runs: int
    deleted_replay_runs: int
    deleted_videos: int
    deleted_screenshots: int
    deleted_traversals: int
    errors: List[str]


@dataclass
class CleanupSummary:
    """Summary of cleanup operation across all tasks."""

    total_tasks_processed: int
    total_tasks_failed: int
    total_deleted_ai_runs: int
    total_deleted_replay_runs: int
    total_deleted_videos: int
    total_deleted_screenshots: int
    total_deleted_traversals: int
    task_results: List[TaskCleanupResult]
    errors: List[str]


class RetentionPolicyManager:
    """Manager for retention policy enforcement.

    This class handles cleanup of testcase-related media files and traversal files
    based on simplified retention rules:
    1. Always keep the last N runs (regardless of age)
    2. For remaining runs, keep only those younger than max_age_days
    """

    # Common video formats to check
    VIDEO_FORMATS = {".mp4", ".webm", ".avi", ".mov", ".mkv"}

    def __init__(self, project_root: Path, config: "RetentionPolicyConfig"):
        """Initialize the retention policy manager.

        Args:
            project_root (Path): Root directory of the Bugninja project
            config (RetentionPolicyConfig): Retention policy configuration
        """
        self.project_root = project_root
        self.config = config
        self.tasks_dir = project_root / "tasks"

    def cleanup_all_tasks(self, dry_run: bool = False) -> CleanupSummary:
        """Clean up all tasks in the project.

        Args:
            dry_run (bool): If True, only preview what would be deleted without actually deleting

        Returns:
            CleanupSummary: Summary of cleanup operation
        """
        if not self.tasks_dir.exists():
            logger.warning(f"Tasks directory does not exist: {self.tasks_dir}")
            return CleanupSummary(
                total_tasks_processed=0,
                total_tasks_failed=0,
                total_deleted_ai_runs=0,
                total_deleted_replay_runs=0,
                total_deleted_videos=0,
                total_deleted_screenshots=0,
                total_deleted_traversals=0,
                task_results=[],
                errors=[],
            )

        task_results: List[TaskCleanupResult] = []
        errors: List[str] = []
        total_tasks_failed = 0

        # Find all task directories
        task_dirs = [d for d in self.tasks_dir.iterdir() if d.is_dir()]

        for task_dir in task_dirs:
            try:
                result = self.cleanup_task(task_dir, dry_run=dry_run)
                task_results.append(result)
                if result.errors:
                    total_tasks_failed += 1
                    errors.extend([f"{result.task_name}: {e}" for e in result.errors])
            except Exception as e:
                logger.error(f"Failed to cleanup task {task_dir.name}: {e}", exc_info=True)
                total_tasks_failed += 1
                errors.append(f"{task_dir.name}: {str(e)}")

        return CleanupSummary(
            total_tasks_processed=len(task_dirs),
            total_tasks_failed=total_tasks_failed,
            total_deleted_ai_runs=sum(r.deleted_ai_runs for r in task_results),
            total_deleted_replay_runs=sum(r.deleted_replay_runs for r in task_results),
            total_deleted_videos=sum(r.deleted_videos for r in task_results),
            total_deleted_screenshots=sum(r.deleted_screenshots for r in task_results),
            total_deleted_traversals=sum(r.deleted_traversals for r in task_results),
            task_results=task_results,
            errors=errors,
        )

    def cleanup_task(self, task_path: Path, dry_run: bool = False) -> TaskCleanupResult:
        """Clean up a single task.

        Args:
            task_path (Path): Path to the task directory
            dry_run (bool): If True, only preview what would be deleted without actually deleting

        Returns:
            TaskCleanupResult: Result of cleanup operation for this task
        """
        task_name = task_path.name
        errors: List[str] = []

        try:
            from bugninja_cli.utils.run_history_manager import RunHistoryManager

            history_manager = RunHistoryManager(task_path)
            history = history_manager.load_history()
        except FileNotFoundError:
            # No run history, nothing to clean up
            return TaskCleanupResult(
                task_name=task_name,
                deleted_ai_runs=0,
                deleted_replay_runs=0,
                deleted_videos=0,
                deleted_screenshots=0,
                deleted_traversals=0,
                errors=[],
            )
        except Exception as e:
            error_msg = f"Failed to load run history: {e}"
            logger.error(error_msg)
            return TaskCleanupResult(
                task_name=task_name,
                deleted_ai_runs=0,
                deleted_replay_runs=0,
                deleted_videos=0,
                deleted_screenshots=0,
                deleted_traversals=0,
                errors=[error_msg],
            )

        # Process AI runs and replay runs separately
        ai_runs = history.get("ai_navigated_runs", [])
        replay_runs = history.get("replay_runs", [])

        # Get runs to delete for each type
        ai_runs_to_delete = self._get_runs_to_delete(ai_runs, "ai_navigated")
        replay_runs_to_delete = self._get_runs_to_delete(replay_runs, "replay")

        # Track deletion counts
        deleted_ai_runs = 0
        deleted_replay_runs = 0
        deleted_videos = 0
        deleted_screenshots = 0
        deleted_traversals = 0

        # Process AI runs
        for run_id in ai_runs_to_delete:
            try:
                media = self._find_media_files(task_path, run_id)
                deleted_count = self._delete_run_media(task_path, run_id, media, dry_run=dry_run)
                deleted_ai_runs += 1
                deleted_videos += deleted_count["videos"]
                deleted_screenshots += deleted_count["screenshots"]
                deleted_traversals += deleted_count["traversals"]
            except Exception as e:
                error_msg = f"Failed to delete media for AI run {run_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Process replay runs
        for run_id in replay_runs_to_delete:
            try:
                media = self._find_media_files(task_path, run_id)
                deleted_count = self._delete_run_media(task_path, run_id, media, dry_run=dry_run)
                deleted_replay_runs += 1
                deleted_videos += deleted_count["videos"]
                deleted_screenshots += deleted_count["screenshots"]
                deleted_traversals += deleted_count["traversals"]
            except Exception as e:
                error_msg = f"Failed to delete media for replay run {run_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Update run history if not dry run
        if not dry_run and (ai_runs_to_delete or replay_runs_to_delete):
            try:
                self._update_run_history(
                    history_manager, history, ai_runs_to_delete, replay_runs_to_delete
                )
            except Exception as e:
                error_msg = f"Failed to update run history: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Clean up empty directories
        if not dry_run:
            self._cleanup_empty_directories(task_path)

        return TaskCleanupResult(
            task_name=task_name,
            deleted_ai_runs=deleted_ai_runs,
            deleted_replay_runs=deleted_replay_runs,
            deleted_videos=deleted_videos,
            deleted_screenshots=deleted_screenshots,
            deleted_traversals=deleted_traversals,
            errors=errors,
        )

    def _get_runs_to_delete(self, runs: List[Dict[str, Any]], run_type: str) -> List[str]:
        """Get list of run IDs to delete based on simplified retention rules.

        Simplified retention policy:
        1. Always keep the last N runs (regardless of age)
        2. For remaining runs, keep only those younger than max_age_days

        Args:
            runs (List[Dict[str, Any]]): List of run entries from run_history.json
            run_type (str): Type of runs ("ai_navigated" or "replay")

        Returns:
            List[str]: List of run IDs to delete
        """
        if not runs:
            return []

        # Parse timestamps and create run entries with run_id and timestamp
        run_entries: List[tuple[str, datetime]] = []
        for run in runs:
            try:
                timestamp_str = run.get("timestamp", "")
                if not timestamp_str:
                    continue

                # Parse ISO timestamp (handle both with and without 'Z' suffix)
                if timestamp_str.endswith("Z"):
                    timestamp = datetime.fromisoformat(timestamp_str[:-1]).replace(tzinfo=UTC)
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=UTC)

                run_id = run.get("run_id", "")
                if run_id:
                    run_entries.append((run_id, timestamp))
            except Exception as e:
                logger.warning(f"Failed to parse timestamp for run: {e}")
                continue

        if not run_entries:
            return []

        # Sort by timestamp (newest first)
        run_entries.sort(key=lambda x: x[1], reverse=True)

        # Calculate cutoff date (runs older than this will be deleted)
        cutoff_date = datetime.now(UTC) - timedelta(days=self.config.max_age_days)

        # Rule 1: Always keep the last N runs (first N in sorted list, regardless of age)
        keep_last_n_ids: Set[str] = {
            run_id for run_id, _ in run_entries[: self.config.keep_last_runs]
        }

        # Rule 2: For remaining runs (after the first N), keep only those younger than max_age_days
        runs_to_delete: List[str] = []
        for run_id, timestamp in run_entries[self.config.keep_last_runs :]:
            # Skip runs that are already protected by Rule 1
            if run_id in keep_last_n_ids:
                continue
            # Delete runs older than cutoff date
            if timestamp < cutoff_date:
                runs_to_delete.append(run_id)

        return runs_to_delete

    def _find_media_files(self, task_path: Path, run_id: str) -> MediaFiles:
        """Find all media files associated with a run.

        Args:
            task_path (Path): Path to the task directory
            run_id (str): Run ID to find media for

        Returns:
            MediaFiles: Container with paths to media files
        """
        media = MediaFiles()

        # Find video file
        videos_dir = task_path / "videos"
        if videos_dir.exists():
            # Check for video files with run_id as base name
            for video_format in self.VIDEO_FORMATS:
                video_file = videos_dir / f"{run_id}{video_format}"
                if video_file.exists():
                    media.video_file = video_file
                    break

        # Find screenshot directory
        screenshots_dir = task_path / "screenshots" / run_id
        if screenshots_dir.exists() and screenshots_dir.is_dir():
            media.screenshot_dir = screenshots_dir

        # Traversal file path is stored in run_history.json
        # We'll get it from the run entry when we have access to it
        # For now, we'll search for it in the traversals directory
        traversals_dir = task_path / "traversals"
        if traversals_dir.exists():
            # Look for traversal files that might contain the run_id
            # Traversal files are typically JSON files
            for traversal_file in traversals_dir.glob("*.json"):
                # Check if filename contains run_id or if it's a common pattern
                if run_id in traversal_file.stem:
                    media.traversal_file = traversal_file
                    break

        return media

    def _delete_run_media(
        self, task_path: Path, run_id: str, media: MediaFiles, dry_run: bool = False
    ) -> Dict[str, int]:
        """Delete media files for a run.

        Args:
            task_path (Path): Path to the task directory
            run_id (str): Run ID
            media (MediaFiles): Media files to delete
            dry_run (bool): If True, only log what would be deleted

        Returns:
            Dict[str, int]: Count of deleted files by type
        """
        deleted_count = {"videos": 0, "screenshots": 0, "traversals": 0}

        # Delete video file
        if media.video_file and media.video_file.exists():
            if dry_run:
                logger.info(f"[DRY RUN] Would delete video: {media.video_file}")
            else:
                try:
                    media.video_file.unlink()
                    logger.info(f"Deleted video: {media.video_file}")
                    deleted_count["videos"] = 1
                except Exception as e:
                    logger.error(f"Failed to delete video {media.video_file}: {e}")

        # Delete screenshot directory
        if media.screenshot_dir and media.screenshot_dir.exists():
            if dry_run:
                screenshot_count = len(list(media.screenshot_dir.glob("*")))
                logger.info(
                    f"[DRY RUN] Would delete {screenshot_count} screenshots from: {media.screenshot_dir}"
                )
            else:
                try:
                    screenshot_count = len(list(media.screenshot_dir.glob("*")))
                    shutil.rmtree(media.screenshot_dir)
                    logger.info(
                        f"Deleted {screenshot_count} screenshots from: {media.screenshot_dir}"
                    )
                    deleted_count["screenshots"] = screenshot_count
                except Exception as e:
                    logger.error(
                        f"Failed to delete screenshot directory {media.screenshot_dir}: {e}"
                    )

        # Delete traversal file (if configured to do so)
        if (
            self.config.cleanup_traversals
            and media.traversal_file
            and media.traversal_file.exists()
        ):
            if dry_run:
                logger.info(f"[DRY RUN] Would delete traversal: {media.traversal_file}")
            else:
                try:
                    media.traversal_file.unlink()
                    logger.info(f"Deleted traversal: {media.traversal_file}")
                    deleted_count["traversals"] = 1
                except Exception as e:
                    logger.error(f"Failed to delete traversal {media.traversal_file}: {e}")

        # Also check run_history.json for traversal_path and delete that file if it exists
        if self.config.cleanup_traversals:
            try:
                from bugninja_cli.utils.run_history_manager import RunHistoryManager

                history_manager = RunHistoryManager(task_path)
                history = history_manager.load_history()

                # Check both AI runs and replay runs for this run_id
                for run_list in [
                    history.get("ai_navigated_runs", []),
                    history.get("replay_runs", []),
                ]:
                    for run in run_list:
                        if run.get("run_id") == run_id:
                            traversal_path_str = run.get("traversal_path", "")
                            if traversal_path_str:
                                traversal_path = Path(traversal_path_str)
                                # Handle relative paths
                                if not traversal_path.is_absolute():
                                    traversal_path = task_path / traversal_path

                                if (
                                    traversal_path.exists()
                                    and traversal_path != media.traversal_file
                                ):
                                    if dry_run:
                                        logger.info(
                                            f"[DRY RUN] Would delete traversal: {traversal_path}"
                                        )
                                    else:
                                        try:
                                            traversal_path.unlink()
                                            logger.info(f"Deleted traversal: {traversal_path}")
                                            deleted_count["traversals"] += 1
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to delete traversal {traversal_path}: {e}"
                                            )
                            break
            except Exception as e:
                logger.warning(f"Failed to check traversal_path from run_history: {e}")

        return deleted_count

    def _update_run_history(
        self,
        history_manager: Any,
        history: Dict[str, Any],
        ai_runs_to_delete: List[str],
        replay_runs_to_delete: List[str],
    ) -> None:
        """Update run_history.json by removing deleted run entries.

        Args:
            history_manager: RunHistoryManager instance
            history (Dict[str, Any]): Current run history data
            ai_runs_to_delete (List[str]): List of AI run IDs to remove
            replay_runs_to_delete (List[str]): List of replay run IDs to remove
        """
        runs_to_delete_set = set(ai_runs_to_delete + replay_runs_to_delete)

        # Filter out deleted runs from AI runs
        ai_runs = history.get("ai_navigated_runs", [])
        ai_runs = [run for run in ai_runs if run.get("run_id") not in runs_to_delete_set]
        history["ai_navigated_runs"] = ai_runs

        # Filter out deleted runs from replay runs
        replay_runs = history.get("replay_runs", [])
        replay_runs = [run for run in replay_runs if run.get("run_id") not in runs_to_delete_set]
        history["replay_runs"] = replay_runs

        # Recalculate summary
        history["summary"] = {
            "total_ai_runs": len(ai_runs),
            "total_replay_runs": len(replay_runs),
            "successful_ai_runs": sum(1 for run in ai_runs if run.get("status") == "success"),
            "successful_replay_runs": sum(
                1 for run in replay_runs if run.get("status") == "success"
            ),
        }

        # Save updated history
        history_manager.save_history(history)

    def _cleanup_empty_directories(self, task_path: Path) -> None:
        """Clean up empty directories after file deletion.

        Args:
            task_path (Path): Path to the task directory
        """
        # Clean up empty screenshot directories
        screenshots_dir = task_path / "screenshots"
        if screenshots_dir.exists():
            for subdir in screenshots_dir.iterdir():
                if subdir.is_dir() and not any(subdir.iterdir()):
                    try:
                        subdir.rmdir()
                        logger.debug(f"Removed empty directory: {subdir}")
                    except Exception as e:
                        logger.warning(f"Failed to remove empty directory {subdir}: {e}")

        # Clean up empty videos directory (optional - might want to keep it)
        # videos_dir = task_path / "videos"
        # if videos_dir.exists() and not any(videos_dir.iterdir()):
        #     try:
        #         videos_dir.rmdir()
        #     except Exception:
        #         pass
