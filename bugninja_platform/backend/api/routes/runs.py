"""Test run endpoints for Bugninja Platform."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from bugninja_platform.backend.services.execution_service import ExecutionService
from bugninja_platform.backend.services.run_service import RunService

router = APIRouter()


@router.post("/test-runs/execute-configuration/{test_case_id}/{browser_config_id}")  # Keep full path for compatibility
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
        tasks_dir = project_root / "tasks"
        task_dir = tasks_dir / test_case_id
        traversals_dir = task_dir / "traversals"
        
        # Remember existing traversal files before starting execution
        existing_files = set()
        if traversals_dir.exists():
            existing_files = set(traversals_dir.glob("traverse_*.json"))
        
        # Start execution in background (library will generate its own run_id)
        asyncio.create_task(execute_task_background(project_root, test_case_id))
        
        # Wait for the NEW traversal file to appear (incremental writes start early)
        # The library now writes JSON incrementally, so file appears quickly
        run_id = None
        for attempt in range(20):  # 20 attempts * 0.5s = 10 seconds max
            await asyncio.sleep(0.5)
            if traversals_dir.exists():
                current_files = set(traversals_dir.glob("traverse_*.json"))
                new_files = current_files - existing_files
                if new_files:
                    # Found new file! Extract run_id from filename
                    # Format: traverse_YYYYMMDD_HHMMSS_<run_id>.json
                    newest = max(new_files, key=lambda p: p.stat().st_mtime)
                    run_id = newest.stem.split('_')[-1]
                    break
        
        # Fallback if no file created yet (should rarely happen with incremental writes)
        if not run_id:
            from cuid2 import Cuid
            run_id = Cuid().generate()
            print(f"⚠️ Warning: No traversal file created after 10s, using fallback run_id: {run_id}")

        # Return immediately with RUNNING state and the ACTUAL run_id
        return {
            "id": run_id,
            "test_case": {
                "id": test_case_id,
                "test_name": test_case_id,
                "test_description": "",
                "test_goal": "",
            },
            "current_state": "RUNNING",
            "started_at": None,  # Will be populated from file when polling
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


@router.get("/test-runs")
async def list_all_test_runs(
    request: Request,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """List all test runs across all test cases with pagination.

    Returns a paginated list of all runs with basic metadata sorted by
    start time (newest first).

    Args:
        request (Request): FastAPI request object
        page (int): Page number (1-indexed)
        page_size (int): Number of items per page

    Returns:
        Dict: Paginated response with test runs

    Raises:
        HTTPException: 500 if listing fails
    """
    project_root: Path = request.app.state.project_root

    try:
        run_service = RunService(project_root)
        all_runs = run_service.list_all_runs()
        
        # Calculate pagination
        total_count = len(all_runs)
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_count > 0:
            page = total_pages
        
        # Get page slice
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = all_runs[start_idx:end_idx]
        
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
        raise HTTPException(status_code=500, detail=f"Failed to list test runs: {str(e)}")


@router.get("/test-runs/test-case/{test_case_id}")
async def list_test_case_runs(
    request: Request,
    test_case_id: str,
    page: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    """List all test runs for a specific test case with pagination.

    Args:
        request (Request): FastAPI request object
        test_case_id (str): Test case identifier
        page (int): Page number (1-indexed)
        page_size (int): Number of items per page

    Returns:
        Dict: Paginated response with test runs

    Raises:
        HTTPException: 500 if listing fails
    """
    project_root: Path = request.app.state.project_root

    try:
        run_service = RunService(project_root)
        all_runs = run_service.list_runs_for_test_case(test_case_id)
        
        # Calculate pagination
        total_count = len(all_runs)
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_count > 0:
            page = total_pages
        
        # Get page slice
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = all_runs[start_idx:end_idx]
        
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
        raise HTTPException(
            status_code=500, detail=f"Failed to list runs for test case '{test_case_id}': {str(e)}"
        )


@router.post("/test-runs/replay/{run_id}")
async def replay_test_run(
    request: Request,
    run_id: str,
    healing: bool = False,
) -> Dict[str, Any]:
    """Replay a recorded test run (traversal) with optional healing.

    Finds the traversal file by run_id and replays it using the replication
    engine. Optionally enables healing to adapt to page changes.

    Args:
        request (Request): FastAPI request object
        run_id (str): Run ID (traversal ID) to replay
        healing (bool): Whether to enable healing during replay (default: False)

    Returns:
        Dict: Initial replay run data with RUNNING state

    Raises:
        HTTPException: 404 if traversal not found
        HTTPException: 500 if replay fails to start
    """
    project_root: Path = request.app.state.project_root

    try:
        # Find the traversal file
        run_service = RunService(project_root)
        traversal_file = run_service.find_traversal_file(run_id)

        if not traversal_file:
            raise HTTPException(
                status_code=404,
                detail=f"Traversal with run_id '{run_id}' not found"
            )

        # Get the task directory to track new replay traversals
        task_dir = traversal_file.parent.parent
        traversals_dir = task_dir / "traversals"
        
        # Remember existing traversal files before replay
        existing_files = set()
        if traversals_dir.exists():
            existing_files = set(traversals_dir.glob("traverse_*.json"))

        # Start replay in background (healing enabled or disabled)
        asyncio.create_task(
            execute_replay_background(project_root, traversal_file, healing)
        )

        # Wait for the NEW replay traversal file to appear
        new_run_id = None
        for attempt in range(20):  # 10 seconds max
            await asyncio.sleep(0.5)
            if traversals_dir.exists():
                current_files = set(traversals_dir.glob("traverse_*.json"))
                new_files = current_files - existing_files
                if new_files:
                    # Found new replay file! Extract run_id
                    newest = max(new_files, key=lambda p: p.stat().st_mtime)
                    new_run_id = newest.stem.split('_')[-1]
                    break

        # Fallback if no file created yet
        if not new_run_id:
            from cuid2 import Cuid
            new_run_id = Cuid().generate()
            print(f"⚠️ Warning: No replay traversal file created after 10s, using fallback run_id: {new_run_id}")

        # Return immediately with RUNNING state
        return {
            "id": new_run_id,
            "test_case": {
                "id": task_dir.name,
                "test_name": task_dir.name,
                "test_description": "",
                "test_goal": "",
            },
            "current_state": "RUNNING",
            "started_at": None,
            "finished_at": None,
            "run_type": "REPLAY",
            "origin": "WEB_UI",
            "healing_enabled": healing,
            "original_run_id": run_id,
            "browser_config": None,
            "brain_states": [],
            "run_gif": None,
            "test_traversal_id": new_run_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start replay: {str(e)}"
        )


async def execute_task_background(project_root: Path, test_case_id: str) -> None:
    """Execute task in background.

    This function is called as an async task. It runs the task using
    PipelineExecutor and handles any errors. The library generates its
    own run_id which is extracted from the traversal filename.

    Args:
        project_root (Path): Project root directory
        test_case_id (str): Task identifier
    """
    try:
        execution_service = ExecutionService(project_root)
        # Execute task - library generates its own run_id
        await execution_service.execute_task(test_case_id)
    except Exception as e:
        # Log error but don't raise (background task)
        print(f"Background task execution failed: {e}")
        import traceback

        traceback.print_exc()


async def execute_replay_background(
    project_root: Path, traversal_file: Path, healing: bool
) -> None:
    """Execute replay in background.

    This function replays a traversal file using TaskExecutor. The library
    generates a new run_id for the replay which is extracted from the
    new traversal filename.

    Args:
        project_root (Path): Project root directory
        traversal_file (Path): Path to the traversal file to replay
        healing (bool): Whether to enable healing during replay
    """
    try:
        # Use TaskExecutor to replay
        from bugninja.schemas import TaskRunConfig
        from bugninja_cli.utils.task_executor import TaskExecutor

        # Create default config
        config = TaskRunConfig()
        
        async with TaskExecutor(config, project_root) as executor:
            result = await executor.replay_traversal(
                traversal_file, enable_healing=healing
            )
            
            if result.success:
                print(f"✅ Replay completed successfully in {result.execution_time:.2f}s")
            else:
                print(f"❌ Replay failed: {result.error_message}")

    except Exception as e:
        # Log error but don't raise (background task)
        print(f"Background replay execution failed: {e}")
        import traceback

        traceback.print_exc()
