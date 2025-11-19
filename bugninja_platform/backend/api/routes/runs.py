"""Test run endpoints for Bugninja Platform."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from bugninja_platform.backend.services.execution_service import ExecutionService
from bugninja_platform.backend.services.run_service import RunService

router = APIRouter()


@router.post("/test-runs/execute-configuration/{test_case_id}/{browser_config_id}")
async def execute_test_configuration(
    request: Request,
    test_case_id: str,
    browser_config_id: str,
) -> Dict[str, Any]:
    """Execute a test configuration.

    This endpoint starts test execution in the background and returns immediately
    with a run ID. The frontend can then poll the run details endpoint to get
    real-time updates.

    Note: We let PipelineExecutor generate its own run_id (CUID) which is used
    in the traversal filename. We start execution and immediately look for the
    new traversal file to get the real run_id.

    Args:
        request (Request): FastAPI request object
        test_case_id (str): Task/test case identifier
        browser_config_id (str): Browser configuration ID (currently unused)

    Returns:
        Dict: Initial run data with RUNNING state

    Raises:
        HTTPException: 404 if task not found
        HTTPException: 500 if execution fails to start
    """

    project_root: Path = request.app.state.project_root

    try:
        # Generate run_id FIRST, before starting execution
        from cuid2 import Cuid

        run_id = Cuid().generate()

        # Start execution in a fire-and-forget task, passing the run_id
        asyncio.create_task(execute_task_background(project_root, test_case_id, run_id))

        # Return immediately with RUNNING state
        return {
            "id": run_id,
            "test_case": {
                "id": test_case_id,
                "test_name": test_case_id,
                "test_description": "",
                "test_goal": "",
            },
            "current_state": "RUNNING",
            "started_at": None,  # Will be set when polling
            "finished_at": None,
            "run_type": "AGENTIC",
            "origin": "WEB_UI",
            "browser_config": {"id": browser_config_id, "browser_config": {}},
            "brain_states": [],
            "run_gif": None,
            "test_traversal_id": run_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start test execution: {str(e)}")


@router.get("/test-runs/{run_id}")
async def get_test_run(request: Request, run_id: str) -> Dict[str, Any]:
    """Get test run details by run ID.

    This endpoint is polled by the frontend every 3 seconds to get real-time
    updates on test execution progress. It reads the traversal file and returns
    the current state with all brain states captured so far.

    Args:
        request (Request): FastAPI request object
        run_id (str): Test run identifier

    Returns:
        Dict: Test run data including current state and brain states

    Raises:
        HTTPException: 404 if run not found after reasonable time
        HTTPException: 500 if data transformation fails
    """
    project_root: Path = request.app.state.project_root

    try:
        run_service = RunService(project_root)
        run_details = run_service.get_run_details(run_id)

        if run_details is None:
            raise HTTPException(status_code=404, detail=f"Test run '{run_id}' not found")

        return run_details

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get test run details: {str(e)}")


async def execute_task_background(project_root: Path, test_case_id: str, run_id: str) -> None:
    """Execute task in background with a pre-generated run_id.

    This function is called as an async task. It runs the task using
    PipelineExecutor and handles any errors. The run_id is provided
    by the caller and should be used for the traversal file.

    Args:
        project_root (Path): Project root directory
        test_case_id (str): Task identifier
        run_id (str): Pre-generated run ID for this execution
    """
    try:
        execution_service = ExecutionService(project_root)
        # Execute task with the provided run_id
        await execution_service.execute_task(test_case_id, run_id=run_id)
    except Exception as e:
        # Log error but don't raise (background task)
        print(f"Background task execution failed: {e}")
        import traceback

        traceback.print_exc()
