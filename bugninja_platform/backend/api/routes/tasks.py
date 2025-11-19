"""Task management endpoints for Bugninja Platform."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bugninja_platform.backend.services.task_service import TaskService
from bugninja_platform.backend.services.task_management_service import TaskManagementService

router = APIRouter()


# Request/Response models for test case CRUD
class CreateTestCaseRequest(BaseModel):
    """Request model for creating a new test case."""
    test_name: str
    test_description: str
    test_goal: str
    url_route: str
    extra_rules: List[str] = []
    allowed_domains: List[str] = []
    priority: str = "medium"
    category: Optional[str] = None


class UpdateTestCaseRequest(BaseModel):
    """Request model for updating a test case."""
    test_name: Optional[str] = None
    test_description: Optional[str] = None
    test_goal: Optional[str] = None
    url_route: Optional[str] = None
    extra_rules: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    priority: Optional[str] = None
    category: Optional[str] = None


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


@router.post("/test-cases/")
async def create_test_case(
    request: Request, test_case_data: CreateTestCaseRequest
) -> Dict[str, Any]:
    """Create a new test case.

    This endpoint creates a new task folder with TOML configuration file
    and returns the created task details.

    Args:
        request (Request): FastAPI request object
        test_case_data (CreateTestCaseRequest): Test case creation data

    Returns:
        Dict: Created test case information in frontend format

    Raises:
        HTTPException: 400 if task already exists
        HTTPException: 500 if creation fails
    """
    project_root: Path = request.app.state.project_root

    try:
        # Create task using management service
        management_service = TaskManagementService(project_root)
        created_info = management_service.create_task(
            test_name=test_case_data.test_name,
            test_description=test_case_data.test_description,
            test_goal=test_case_data.test_goal,
            url_route=test_case_data.url_route,
            extra_rules=test_case_data.extra_rules,
            allowed_domains=test_case_data.allowed_domains,
            priority=test_case_data.priority,
            category=test_case_data.category,
        )

        # Return full task details using task service
        task_service = TaskService(project_root)
        task = task_service.get_task(created_info["folder_name"])

        return task

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test case: {str(e)}")


@router.put("/test-cases/{task_identifier}")
async def update_test_case(
    request: Request, task_identifier: str, updates: UpdateTestCaseRequest
) -> Dict[str, Any]:
    """Update an existing test case.

    This endpoint updates the task's TOML configuration file with the
    provided changes and returns the updated task details.

    Args:
        request (Request): FastAPI request object
        task_identifier (str): Task identifier (name, folder, or CUID)
        updates (UpdateTestCaseRequest): Fields to update

    Returns:
        Dict: Updated test case information in frontend format

    Raises:
        HTTPException: 404 if task not found
        HTTPException: 500 if update fails
    """
    project_root: Path = request.app.state.project_root

    try:
        # Filter out None values from updates
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}

        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update task using management service
        management_service = TaskManagementService(project_root)
        management_service.update_task(task_identifier, update_dict)

        # Return updated task details using task service
        task_service = TaskService(project_root)
        task = task_service.get_task(task_identifier)

        return task

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update test case: {str(e)}")


@router.delete("/test-cases/{task_identifier}")
async def delete_test_case(request: Request, task_identifier: str) -> Dict[str, str]:
    """Delete a test case and all its associated data.

    This endpoint removes the entire task folder including configuration,
    traversals, screenshots, and videos.

    Args:
        request (Request): FastAPI request object
        task_identifier (str): Task identifier (name, folder, or CUID)

    Returns:
        Dict: Deletion confirmation message

    Raises:
        HTTPException: 404 if task not found
        HTTPException: 500 if deletion fails
    """
    project_root: Path = request.app.state.project_root

    try:
        # Delete task using management service
        management_service = TaskManagementService(project_root)
        result = management_service.delete_task(task_identifier)

        return {
            "message": f"Test case '{result['folder_name']}' deleted successfully",
            "deleted": True,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test case: {str(e)}")
