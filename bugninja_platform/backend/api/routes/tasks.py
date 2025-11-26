"""Task management endpoints for Bugninja Platform."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bugninja_platform.backend.services.task_service import TaskService
from bugninja_platform.backend.services.task_management_service import TaskManagementService

router = APIRouter()


# Stub endpoints for browser configs and secrets (to be implemented)
@router.get("/browser-types")
async def get_browser_types() -> Dict[str, Any]:
    """Get available browser types and configuration options."""
    return {
        "browser_channels": [
            "chromium",
            "firefox",
            "webkit"
        ],
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ],
        "viewport_sizes": [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 768, "height": 1024},
            {"width": 375, "height": 667}
        ]
    }


@router.get("/browser-configs/project/{project_id}")
async def get_browser_configs(project_id: str) -> List[Dict[str, Any]]:
    """Get browser configurations for project (stub)."""
    return []


@router.get("/secret-values/project/{project_id}")
async def get_secret_values(project_id: str) -> List[Dict[str, Any]]:
    """Get secret values for project (stub)."""
    return []


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
    # Optional fields for multi-project support (ignored for now)
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    # Browser configs and secrets (stubs for now, not yet implemented)
    new_browser_configs: Optional[List[Dict[str, Any]]] = None
    existing_browser_config_ids: Optional[List[str]] = None
    new_secret_values: Optional[List[Dict[str, Any]]] = None
    existing_secret_value_ids: Optional[List[str]] = None


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
async def list_tasks(
    request: Request,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """List all tasks in the current project with pagination support.

    Reads all task TOML files from the `tasks/` directory and returns
    their information in a paginated format compatible with the frontend.

    Args:
        request (Request): FastAPI request object (provides access to app state)
        page (int): Page number (1-indexed)
        page_size (int): Number of items per page

    Returns:
        Dict: Paginated response containing:
            - items: List of task information dictionaries
            - total_count: Total number of tasks
            - page: Current page number
            - page_size: Items per page
            - total_pages: Total number of pages
            - has_next: Whether there's a next page
            - has_previous: Whether there's a previous page

    Raises:
        HTTPException: 500 if task listing fails
    """
    project_root: Path = request.app.state.project_root

    try:
        service = TaskService(project_root)
        all_tasks = service.list_tasks()
        
        # Calculate pagination
        total_count = len(all_tasks)
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_count > 0:
            page = total_pages
        
        # Get page slice
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = all_tasks[start_idx:end_idx]
        
        return {
            "items": items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
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

        # Return in format expected by frontend
        # Frontend checks for fullResponse.test_case first, then falls back to fullResponse
        return {
            "test_case": task,
            "created_browser_configs": [],  # Stub for now
            "created_secret_values": []  # Stub for now
        }

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
            "task_id": result['task_id'],
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test case: {str(e)}")
