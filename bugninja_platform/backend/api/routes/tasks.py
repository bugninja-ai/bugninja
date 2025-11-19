"""Task management endpoints for Bugninja Platform."""

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from bugninja_platform.backend.services.task_service import TaskService

router = APIRouter()


@router.get("/tasks")
async def list_tasks(request: Request) -> List[Dict[str, Any]]:
    """List all tasks in the current project.

    Reads all task TOML files from the `tasks/` directory and returns
    their information in a structured format.

    Args:
        request (Request): FastAPI request object (provides access to app state)

    Returns:
        List[Dict]: List of task information dictionaries, each containing:
            - id: Task identifier (folder name)
            - name: Task display name
            - description: Task description
            - start_url: Starting URL
            - folder_name: Task folder name
            - toml_path: Path to TOML file
            - created_date: Creation timestamp
            - extra_instructions: List of extra instructions
            - dependencies: List of dependent tasks

    Raises:
        HTTPException: 500 if task listing fails
    """
    project_root: Path = request.app.state.project_root

    try:
        service = TaskService(project_root)
        tasks = service.list_tasks()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/tasks/{task_identifier}")
async def get_task(request: Request, task_identifier: str) -> Dict[str, Any]:
    """Get details for a specific task.

    Args:
        request (Request): FastAPI request object
        task_identifier (str): Task identifier (name, folder name, or CUID)

    Returns:
        Dict: Task information dictionary with full details

    Raises:
        HTTPException: 404 if task not found
        HTTPException: 500 if task retrieval fails
    """
    project_root: Path = request.app.state.project_root

    try:
        service = TaskService(project_root)
        task = service.get_task(task_identifier)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_identifier}' not found")

        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")
