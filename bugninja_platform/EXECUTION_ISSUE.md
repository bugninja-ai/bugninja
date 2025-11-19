# Execution Issue Analysis

## Problem

When we call:
```
POST /test-runs/execute-configuration/1_simple_navigation/1_simple_navigation_default
```

**What happens:**
1. ✅ Endpoint returns immediately with run_id
2. ✅ Background task is added to FastAPI
3. ❌ No traversal file is created
4. ❌ Task doesn't actually execute

## Root Cause

### Issue 1: Background Task Execution
FastAPI's `BackgroundTasks` doesn't work as expected with async functions that use `PipelineExecutor`.

The background task adds the task to the queue, but:
- It may not have enough time to complete
- It may be killed when the request finishes
- Errors are silently swallowed

### Issue 2: Run ID Not Passed to PipelineExecutor

Even if it did execute:
```python
# We generate:
run_id = "hqzm1eu04iob2wapxri32xw2"

# But PipelineExecutor generates its own:
# - It creates a CUID internally
# - Uses it for the traversal filename
# - We can't control it from outside
```

So the file would be named:
```
traverse_20251117_112650_PIPELINE_GENERATED_ID.json
```

Not:
```
traverse_20251117_112650_hqzm1eu04iob2wapxri32xw2.json
```

## Solutions

### Option A: Return Pipeline's Run ID (Recommended)

**Change flow:**
1. Start task execution
2. Get the traversal ID that PipelineExecutor generates
3. Return THAT as the run_id to frontend

**Problem:** 
- We want non-blocking (return immediately)
- But need the ID from PipelineExecutor
- Can't have both...

### Option B: Use a Process Pool for Background Execution

Instead of FastAPI BackgroundTasks, use a proper process pool:

```python
from concurrent.futures import ProcessPoolExecutor
import asyncio

executor = ProcessPoolExecutor(max_workers=4)

@app.post("/test-runs/execute-configuration/{task_id}/{browser_config_id}")
async def execute_test(task_id: str):
    run_id = generate_run_id()
    
    # Submit to process pool (truly runs in background)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_task_sync, task_id, run_id)
    
    return {"id": run_id, "current_state": "RUNNING", ...}
```

**Problem:**
- Still can't pass run_id to PipelineExecutor
- It generates its own

### Option C: CLI Command Execution (Simplest)

Just run the CLI command in a subprocess:

```python
import subprocess

@app.post("/test-runs/execute-configuration/{task_id}/{browser_config_id}")
async def execute_test(task_id: str):
    # Run CLI command in background
    process = subprocess.Popen(
        ["bugninja", "run", task_id],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # The CLI will generate its own traversal file
    # We need to wait a moment to get the run_id from the file
    await asyncio.sleep(1)
    
    # Find the newly created traversal file
    run_id = find_latest_traversal_run_id(task_id)
    
    return {"id": run_id, "current_state": "RUNNING", ...}
```

**Pros:**
- Uses existing, tested CLI
- Traversal file guaranteed to be created
- Run ID matches what's actually used

**Cons:**
- Need to wait ~1 second to get run_id
- Have to find the file by scanning directory

### Option D: Modify PipelineExecutor to Accept Run ID

Change the PipelineExecutor code to accept an optional run_id parameter.

**Pros:**
- Clean solution
- Full control

**Cons:**
- Requires modifying core library code
- May break other things

## Recommended Solution: Option C (CLI Subprocess)

This is the most pragmatic:

```python
async def execute_test_configuration(task_id: str, browser_config_id: str):
    project_root = get_project_root()
    
    # Start CLI command in background
    process = subprocess.Popen(
        ["uv", "run", "bugninja", "run", task_id],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait briefly for traversal file to be created
    await asyncio.sleep(2)
    
    # Find the newest traversal file for this task
    traversals_dir = project_root / "tasks" / task_id / "traversals"
    traversal_files = list(traversals_dir.glob("traverse_*.json"))
    
    if traversal_files:
        # Get newest file
        newest = max(traversal_files, key=lambda p: p.stat().st_mtime)
        # Extract run_id from filename: traverse_DATE_TIME_RUNID.json
        run_id = newest.stem.split('_')[-1]
    else:
        # Fallback: generate temporary ID
        run_id = generate_run_id()
    
    return {
        "id": run_id,
        "current_state": "RUNNING",
        ...
    }
```

This way:
- Task actually executes (using proven CLI)
- We get the real run_id
- Polling will find the correct file
- 2-second delay is acceptable for starting a test

## Current State

Right now:
- ❌ Background task doesn't execute (or fails silently)
- ❌ No traversal file created
- ❌ Polling returns RUNNING forever (file never appears)
- ✅ API structure is correct
- ✅ Polling logic works
- ✅ Transformation logic works

Need to fix the execution method to actually run the task.


