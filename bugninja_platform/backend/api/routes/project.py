"""Project management endpoints for Bugninja Platform."""

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bugninja_platform.backend.services.project_service import ProjectService

router = APIRouter()


class ProjectUpdateRequest(BaseModel):
    """Request model for updating project information.

    Attributes:
        name (Optional[str]): New project name
        default_start_url (Optional[str]): New default start URL
    """

    name: Optional[str] = None
    default_start_url: Optional[str] = None


@router.get("/project")
async def get_project(request: Request) -> Dict[str, Any]:
    """Get current project information.

    Reads and returns project configuration from `bugninja.toml`.

    Args:
        request (Request): FastAPI request object (provides access to app state)

    Returns:
        dict: Project information including:
            - id: Project identifier
            - name: Project name
            - default_start_url: Default starting URL
            - created_at: Creation timestamp
            - updated_at: Last modified timestamp
            - tasks_dir: Path to tasks directory
            - project_root: Project root directory path

    Raises:
        HTTPException: 404 if bugninja.toml not found
        HTTPException: 500 if configuration parsing fails
    """
    project_root: Path = request.app.state.project_root

    try:
        service = ProjectService(project_root)
        project_info = service.get_project_info()
        return project_info
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read project info: {str(e)}")


@router.put("/project")
async def update_project(request: Request, update_data: ProjectUpdateRequest) -> Dict[str, Any]:
    """Update project information.

    Updates project configuration in `bugninja.toml`.

    Args:
        request (Request): FastAPI request object
        update_data (ProjectUpdateRequest): Fields to update

    Returns:
        dict: Updated project information

    Raises:
        HTTPException: 404 if bugninja.toml not found
        HTTPException: 400 if no fields provided to update
        HTTPException: 500 if update fails
    """
    project_root: Path = request.app.state.project_root

    # Check if any fields provided
    if update_data.name is None and update_data.default_start_url is None:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        service = ProjectService(project_root)
        updated_info = service.update_project_info(
            name=update_data.name, default_start_url=update_data.default_start_url
        )
        return updated_info
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")
