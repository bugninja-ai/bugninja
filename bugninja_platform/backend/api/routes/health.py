"""Health check endpoint for Bugninja Platform."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Health check endpoint.

    Returns basic platform status and project information.

    Args:
        project_root (Optional[Path]): Root directory of the Bugninja project

    Returns:
        dict: Health status information including:
            - status: Platform operational status
            - timestamp: Current server time
            - project_root: Current project directory (if available)
    """
    response = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": "bugninja",
        "version": "0.1.0",
    }

    if project_root:
        response["project_root"] = str(project_root)

    return response
