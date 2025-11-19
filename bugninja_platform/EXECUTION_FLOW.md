# Task Execution Flow - Detailed Analysis

Based on frontend implementation analysis.

## Complete Execution Flow

### 1. User Clicks "Run Test" Button

**Location:** `TestCaseDetailPage.tsx` or `RecentTestRuns.tsx`

```typescript
// User clicks "Run test" button
handleRunTest() {
  setShowRunTestModal(true);  // Opens modal
}
```

### 2. User Selects Browser Config and Clicks Run

**Location:** `RunTestModal.tsx` → `handleRunConfiguration()`

```typescript
const handleRunConfiguration = async (browserConfig: BrowserConfig) => {
  // 1. Call execute endpoint
  const result = await TestCaseService.executeTestConfiguration(
    testCase.id,           // e.g., "1_simple_navigation"
    browserConfig.id       // e.g., "1_simple_navigation_default"
  );
  
  // 2. Get run ID from response
  const runId = result.id;  // e.g., "ig9k2qu035xdz8x8fgqmcvr4"
  
  // 3. Close modal
  onClose();
  
  // 4. Navigate to test run detail page
  navigate(`/runs/${runId}`);  // → /runs/ig9k2qu035xdz8x8fgqmcvr4
}
```

### 3. Execute Endpoint Called

**API Call:**
```
POST /test-runs/execute-configuration/{testCaseId}/{browserConfigId}
```

**What Backend Must Do:**
1. Start task execution in **background** (non-blocking)
2. Create/track a run ID (use traversal run ID)
3. Return **immediately** with run ID and initial state
4. Task continues executing in background

**Expected Response (immediate):**
```json
{
  "id": "ig9k2qu035xdz8x8fgqmcvr4",  // Run ID for polling
  "test_case": {
    "id": "1_simple_navigation",
    "test_name": "1_simple_navigation",
    "test_description": "...",
    "test_goal": "..."
  },
  "current_state": "RUNNING",  // ⭐ Important: RUNNING, not PENDING
  "started_at": "2025-11-17T12:00:00Z",
  "finished_at": null,
  "run_type": "AGENTIC",
  "origin": "WEB_UI",
  "browser_config": {...},
  "brain_states": [],  // Empty initially
  "run_gif": null,
  "test_traversal_id": "ig9k2qu035xdz8x8fgqmcvr4"
}
```

### 4. Frontend Navigates to Test Run Detail Page

**Location:** `TestRunDetailPage.tsx` → Uses `useTestRunDetail` hook

```typescript
// Page loads with runId from URL
const { runId } = useParams();  // "ig9k2qu035xdz8x8fgqmcvr4"

// Hook automatically:
// 1. Loads test run data
// 2. Checks if status is RUNNING
// 3. Starts polling if RUNNING
```

### 5. Polling Starts

**Location:** `useTestRunDetail.ts` → `startPolling()`

```typescript
useEffect(() => {
  if (runId) {
    // Load initial data
    loadTestRun(runId).then((isStillRunning) => {
      if (isStillRunning) {
        startPolling(runId);  // Start 3-second interval
      }
    });
  }
  
  return () => stopPolling();  // Cleanup on unmount
}, [runId]);

const startPolling = (id: string) => {
  setIsPolling(true);
  pollingIntervalRef.current = setInterval(async () => {
    const isStillRunning = await loadTestRun(id, true);
    if (!isStillRunning) {
      // Stop polling when done
      stopPolling();
    }
  }, 3000);  // ⭐ Poll every 3 seconds
};

const loadTestRun = async (id: string, isPollingCall = false) => {
  // GET /test-runs/{id}
  const backendData = await TestCaseService.getTestRun(id);
  const transformedRun = transformBackendTestRun(backendData);
  
  setTestRun(transformedRun);
  
  // Check if still running
  const isStillRunning = ['pending'].includes(transformedRun.status);
  // Note: 'pending' includes both RUNNING and PENDING states
  
  return isStillRunning;
};
```

### 6. Poll Endpoint Called Every 3 Seconds

**API Call:**
```
GET /test-runs/{runId}
```

**What Backend Must Do:**
1. Read current state of traversal file
2. If file doesn't exist yet → return RUNNING with empty brain_states
3. If file exists but incomplete → return RUNNING with current brain_states
4. If file has "done" action → return FINISHED with all brain_states
5. If error/timeout → return FAILED/ERROR

**Response Evolution:**

**Poll 1 (0 seconds):** File doesn't exist yet
```json
{
  "id": "ig9k2qu035xdz8x8fgqmcvr4",
  "current_state": "RUNNING",
  "brain_states": [],  // Empty, task just started
  "started_at": "2025-11-17T12:00:00Z",
  "finished_at": null
}
```

**Poll 2 (3 seconds):** Partial results
```json
{
  "id": "ig9k2qu035xdz8x8fgqmcvr4",
  "current_state": "RUNNING",
  "brain_states": [
    {
      "id": "state_1",
      "evaluation_previous_goal": "...",
      "next_goal": "Navigate to URL",
      "history_elements": [...]
    }
  ],  // Growing as task executes
  "started_at": "2025-11-17T12:00:00Z",
  "finished_at": null
}
```

**Poll N (60 seconds):** Completed
```json
{
  "id": "ig9k2qu035xdz8x8fgqmcvr4",
  "current_state": "FINISHED",  // ⭐ Changed to FINISHED
  "brain_states": [...],  // All brain states
  "started_at": "2025-11-17T12:00:00Z",
  "finished_at": "2025-11-17T12:01:00Z"  // ⭐ Now has end time
}
```

### 7. Polling Stops

**Condition:** `current_state` is NOT "RUNNING" or "PENDING"

```typescript
// Frontend checks status
const statusMap = {
  'RUNNING': 'pending',
  'PENDING': 'pending',
  'FINISHED': 'passed',
  'FAILED': 'failed',
  'ERROR': 'failed'
};

const mappedStatus = statusMap[backendData.current_state];
const isStillRunning = ['pending'].includes(mappedStatus);

if (!isStillRunning) {
  stopPolling();  // Stop the interval
}
```

### 8. UI Updates During Polling

- **Auto-scroll** to bottom as new brain states arrive
- **Progress indicator** showing "Auto-refreshing every 3 seconds..."
- **Brain states** rendered in real-time
- **Screenshots** displayed as they're captured

## Key Implementation Requirements

### Execute Endpoint
```
POST /api/v1/tasks/{task_name}/run
or
POST /test-runs/execute-configuration/{testCaseId}/{browserConfigId}
```

**Must:**
1. Generate run ID (use PipelineExecutor's traversal ID)
2. Start task execution in **background thread/process**
3. Return immediately (don't wait for completion)
4. Return run object with `current_state: "RUNNING"`

### Get Run Details Endpoint  
```
GET /api/v1/runs/{run_id}
or
GET /test-runs/{run_id}
```

**Must:**
1. Read traversal file from `tasks/{name}/traversals/traverse_*_{run_id}.json`
2. If file doesn't exist → `current_state: "RUNNING"`, empty brain_states
3. If file exists:
   - Has "done" action → `current_state: "FINISHED"`
   - No "done" but has actions → `current_state: "RUNNING"`
   - Has error indicators → `current_state: "FAILED"`
4. Transform traversal JSON to expected format
5. Return with proper brain_states structure

## Critical Notes

1. **Non-blocking execution**: POST must return immediately, task runs in background
2. **Polling interval**: 3 seconds
3. **Stop condition**: When `current_state` is not RUNNING/PENDING
4. **Run ID**: Must match traversal file name (part after last `_`)
5. **Screenshot URLs**: Must be accessible via HTTP (serve static files)
6. **Real-time updates**: GET endpoint reads file on every poll

## Backend Architecture Needed

```python
# Execute endpoint
@app.post("/test-runs/execute-configuration/{task_id}/{browser_config_id}")
async def execute_test(task_id: str, browser_config_id: str, background_tasks: BackgroundTasks):
    # Generate run ID
    run_id = generate_run_id()
    
    # Add background task
    background_tasks.add_task(run_task_in_background, task_id, run_id)
    
    # Return immediately
    return {
        "id": run_id,
        "current_state": "RUNNING",
        "started_at": datetime.now().isoformat(),
        "brain_states": [],
        ...
    }

# Get run details endpoint  
@app.get("/test-runs/{run_id}")
async def get_run_details(run_id: str):
    # Find and read traversal file
    traversal_file = find_traversal_file(run_id)
    
    if not traversal_file or not traversal_file.exists():
        return {
            "id": run_id,
            "current_state": "RUNNING",
            "brain_states": []
        }
    
    # Parse and transform traversal data
    data = parse_traversal_json(traversal_file)
    return transform_to_api_format(data)
```

