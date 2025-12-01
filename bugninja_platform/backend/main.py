"""Main FastAPI application for Bugninja Platform.

This module provides the **FastAPI application** that serves as the backend
for the Bugninja web platform interface.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from bugninja_platform.backend.api.routes import health, project, runs, tasks


def create_app(project_root: Optional[Path] = None) -> FastAPI:
    """Create and configure FastAPI application.

    This function creates the **main FastAPI application** with:
    - CORS middleware for frontend communication
    - API routes for task management
    - Project-specific configuration

    Args:
        project_root (Optional[Path]): Root directory of the Bugninja project.
            If not provided, uses current working directory.

    Returns:
        FastAPI: Configured FastAPI application instance

    Example:
        ```python
        from bugninja_platform.backend.main import create_app
        from pathlib import Path

        app = create_app(Path("/path/to/project"))
        ```
    """
    # Use current directory if no project root provided
    if project_root is None:
        project_root = Path.cwd()

    # Create FastAPI app
    app = FastAPI(
        title="Bugninja Platform API",
        description="REST API for Bugninja browser automation platform",
        version="0.1.0",
    )

    # Configure CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # React dev server
            "http://localhost:8000",  # Self-hosted production build
            "http://127.0.0.1:8000",  # Self-hosted production build (IP)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store project root in app state
    app.state.project_root = project_root

    # Register API routes
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(project.router, prefix="/api/v1", tags=["project"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
    app.include_router(runs.router, prefix="/api/v1", tags=["runs"])  # Add /api/v1 prefix

    # Serve screenshots as static files
    # Screenshots are in tasks/{name}/screenshots/ directories
    tasks_dir = project_root / "tasks"
    if tasks_dir.exists():
        app.mount("/tasks", StaticFiles(directory=str(tasks_dir)), name="tasks")

    # Serve frontend static files (production build)
    # IMPORTANT: Static files must be mounted AFTER API routes but assets BEFORE catch-all
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    print(f"📁 Frontend dist path: {frontend_dist}")
    print(f"📁 Frontend dist exists: {frontend_dist.exists()}")
    
    if frontend_dist.exists():
        print(f"✅ Mounting frontend from {frontend_dist}")
        
        # First mount assets directory for CSS/JS
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            print(f"✅ Mounting assets from {assets_dir}")
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
        # Catch-all route for SPA - MUST BE LAST
        # This serves index.html for any unmatched routes (React Router)
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        print("✅ Frontend static files mounted at /")
    else:
        print(f"⚠️ Frontend dist not found at {frontend_dist}")

    return app
