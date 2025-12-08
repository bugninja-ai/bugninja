"""Main FastAPI application for Bugninja Platform.

This module provides the **FastAPI application** that serves as the backend
for the Bugninja web platform interface.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    print(f"📁 Frontend dist path: {frontend_dist}")
    print(f"📁 Frontend dist exists: {frontend_dist.exists()}")
    
    if frontend_dist.exists():
        print(f"✅ Mounting frontend from {frontend_dist}")
        
        # Mount assets directory for CSS/JS
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            print(f"✅ Mounting assets from {assets_dir}")
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
        # Store frontend_dist in app state for the catch-all route
        app.state.frontend_dist = frontend_dist
        
        # SPA catch-all route - serves index.html for all non-API, non-asset routes
        # This enables client-side routing (React Router) to work on page refresh
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str) -> FileResponse:
            """Serve index.html for SPA routes.
            
            This catch-all route enables React Router to handle client-side navigation.
            On page refresh, the server returns index.html which then bootstraps the
            React app and React Router takes over.
            """
            index_path = app.state.frontend_dist / "index.html"
            return FileResponse(index_path)
        
        print("✅ SPA catch-all route configured")
    else:
        print(f"⚠️ Frontend dist not found at {frontend_dist}")

    return app
