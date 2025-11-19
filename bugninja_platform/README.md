# Bugninja Platform - Web Interface Backend

## Overview

The Bugninja Platform provides a modern web interface for the Bugninja CLI tool. It consists of a **thin FastAPI wrapper** that operates on the existing file-based architecture (no database required) and serves a React frontend.

## Architecture

```
┌─────────────────────────────────────────┐
│         React Frontend (Vite)           │
│   - TypeScript + TailwindCSS            │
│   - Test case management UI             │
│   - Test run visualization              │
└─────────────────────────────────────────┘
                    ↓ HTTP/WebSocket
┌─────────────────────────────────────────┐
│      FastAPI Backend (Thin Wrapper)     │
│   - REST API endpoints                  │
│   - WebSocket for live output           │
│   - File system operations              │
│   - Direct Python imports from bugninja │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│    Bugninja Library (Existing Code)     │
│   - BugninjaPipeline                    │
│   - Task execution                      │
│   - Result processing                   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Filesystem (Source of Truth)       │
│   - tasks/*.toml                        │
│   - results/*/traversal_*.json          │
│   - screenshots/*/                      │
│   - bugninja.toml (project config)      │
└─────────────────────────────────────────┘
```

## Design Principles

### 1. No Database Required
- All data lives in files (TOML, JSON, images)
- FastAPI reads/parses files on demand
- Statistics calculated on-the-fly from result files
- Optional in-memory caching for performance

### 2. Reuse Existing Code
- Import and call existing `bugninja.api.*` modules
- Use existing TOML parsers, pipeline executors, stats collectors
- Don't duplicate CLI logic - call it directly

### 3. File-Based Operations
- Read `tasks/*.toml` for test case listings
- Parse `results/*/traversal_*.json` for run history
- Serve screenshots directly from `screenshots/*/`
- Watch filesystem for changes (optional real-time updates)

### 4. Single Project Mode (Phase 1)
- Platform operates on current working directory
- No multi-project management initially
- Matches CLI behavior: one project per folder
- Can be extended later if needed

## API Design

### Endpoints to Implement

```
GET  /api/v1/health                     # Health check
GET  /api/v1/project                    # Get current project info (from bugninja.toml)
PUT  /api/v1/project                    # Update project settings

GET  /api/v1/tasks                      # List all tasks (read tasks/*.toml)
GET  /api/v1/tasks/{task_name}          # Get task details
POST /api/v1/tasks                      # Create new task (write TOML)
PUT  /api/v1/tasks/{task_name}          # Update task
DELETE /api/v1/tasks/{task_name}        # Delete task

GET  /api/v1/tasks/{task_name}/runs     # List runs for task (scan results/task_name/)
GET  /api/v1/runs/{run_id}              # Get run details (read specific JSON)
POST /api/v1/tasks/{task_name}/run      # Execute task (call pipeline)
POST /api/v1/tasks/{task_name}/replay   # Replay task (call replicator)

GET  /api/v1/stats                      # Overall statistics (aggregate from files)
GET  /api/v1/tasks/{task_name}/stats    # Task-specific stats

WS   /api/v1/tasks/{task_name}/stream   # Live output during execution
```

### Response Transformations

The frontend expects specific JSON structures. The backend must:

1. **Transform TOML → JSON**: Parse `tasks/*.toml` and map to frontend's expected format
2. **Calculate aggregations**: Count passed/failed runs, success rates, last run times
3. **Generate IDs**: Use task names or generate stable IDs from filenames
4. **Handle pagination**: Implement simple in-memory pagination of file listings

## Implementation Strategy

### Phase 1: Core Backend (Week 1)
- [ ] FastAPI app structure
- [ ] Project info endpoints (read/write bugninja.toml)
- [ ] Task CRUD endpoints (read/write tasks/*.toml)
- [ ] Task execution endpoint (call BugninjaPipeline)
- [ ] Results listing (scan results/ folder)
- [ ] Run details endpoint (read traversal JSON)

### Phase 2: Frontend Adaptation (Week 1-2)
- [ ] Remove multi-project logic from frontend
- [ ] Update API endpoints to match new backend
- [ ] Remove project_id from requests
- [ ] Adjust data transformations if needed
- [ ] Test all core workflows

### Phase 3: Advanced Features (Week 2-3)
- [ ] WebSocket for live test output streaming
- [ ] File watcher for real-time updates
- [ ] Screenshot serving
- [ ] Stats aggregation with caching
- [ ] Replay functionality
- [ ] Browser config management

### Phase 4: CLI Integration (Week 3)
- [ ] New `bugninja platform` CLI command
- [ ] Auto-detect if in bugninja project
- [ ] Start FastAPI server + serve React build
- [ ] Graceful shutdown handling
- [ ] Port configuration options

## File Structure

```
bugninja_platform/
├── README.md                    # This file
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── project.py       # Project endpoints
│   │   │   ├── tasks.py         # Task CRUD
│   │   │   ├── runs.py          # Run management
│   │   │   └── stats.py         # Statistics
│   │   └── models.py            # Pydantic response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py      # Task file operations
│   │   ├── run_service.py       # Result file operations
│   │   ├── execution_service.py # Run tests via pipeline
│   │   └── stats_service.py     # Statistics calculation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_watcher.py      # Filesystem monitoring
│   │   └── transformers.py      # TOML/JSON → API format
│   └── config.py                # Server configuration
├── frontend/                    # React app (adapted from frontend-temporary)
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
└── static/                      # Built frontend (after npm build)
```

## Key Code Patterns

### Reading Task Files
```python
from pathlib import Path
from bugninja.config.toml_loader import load_toml

def get_all_tasks() -> List[Dict]:
    tasks_dir = Path("tasks")
    tasks = []
    for toml_file in tasks_dir.glob("*.toml"):
        task_data = load_toml(toml_file)
        tasks.append(transform_task(task_data))
    return tasks
```

### Executing Tasks
```python
from bugninja.api.bugninja_pipeline import BugninjaPipeline

async def execute_task(task_name: str):
    # Import existing pipeline - don't rewrite!
    pipeline = BugninjaPipeline(task_name)
    result = await pipeline.run()
    return result
```

### Calculating Statistics
```python
from bugninja_cli.utils.stats_collector import StatsCollector

def get_task_stats(task_name: str):
    # Reuse CLI stats logic
    collector = StatsCollector(project_path=Path.cwd())
    stats = collector.collect_task_stats(task_name)
    return stats
```

### Streaming Test Output
```python
@app.websocket("/api/v1/tasks/{task_name}/stream")
async def stream_task_execution(websocket: WebSocket, task_name: str):
    await websocket.accept()
    
    # Hook into event system
    from bugninja.events.manager import EventManager
    
    def send_event(event):
        await websocket.send_json({
            "type": event.type,
            "data": event.data
        })
    
    # Execute with custom publisher
    # ... implementation
```

## Frontend Changes Required

### Remove Multi-Project Logic
- Remove `project_id` from API calls
- Remove project selector dropdown
- Remove project creation modal
- Update ProjectContext to work with single project

### Update API Endpoints
```typescript
// Before
GET /api/v1/test-cases/?project_id=abc123

// After  
GET /api/v1/tasks/
```

### Update Data Models
```typescript
// Match backend response format
interface Task {
  id: string;              // task filename or name
  name: string;
  description: string;
  goal: string;
  priority: string;
  // ... rest matches TOML structure
}
```

## CLI Command

```bash
# User runs this in their bugninja project
bugninja platform

# Output:
# 🚀 Starting Bugninja Platform...
# 📂 Project: /Users/john/my_project
# 🌐 Server: http://localhost:8000
# 🎨 Frontend: http://localhost:8000
# 📡 API Docs: http://localhost:8000/docs
# 
# Press Ctrl+C to stop

# Options:
bugninja platform --port 8080        # Custom port
bugninja platform --host 0.0.0.0     # Allow network access
bugninja platform --no-browser       # Don't auto-open browser
```

## Development Workflow

### 1. Backend Development
```bash
cd bugninja_platform/backend
uv run uvicorn main:app --reload --port 8000
```

### 2. Frontend Development
```bash
cd bugninja_platform/frontend
npm run dev  # Runs on 5173, proxies API to 8000
```

### 3. Test in Real Project
```bash
cd examples/testing/cli
uv run python -m bugninja_platform.backend.main
# Frontend calls backend, backend operates on ./tasks, ./results, etc.
```

## Benefits of This Approach

1. **No architectural changes** - Files remain source of truth
2. **Reuse battle-tested code** - CLI logic already works
3. **Fast queries** - For typical project sizes (10-100 tasks), file operations are plenty fast
4. **Simple deployment** - No database setup, migrations, backups
5. **Portable** - Everything in one folder, easy to move/backup
6. **Transparent** - Users can still edit TOML files manually
7. **Progressive enhancement** - Add caching/optimization only if needed

## Next Steps

1. ✅ Create bugninja_platform/ folder structure
2. ⬜ Implement basic FastAPI backend with health check
3. ⬜ Add task listing endpoint (read tasks/*.toml)
4. ⬜ Add task execution endpoint (call pipeline)
5. ⬜ Adapt frontend to remove project_id
6. ⬜ Wire up frontend to new backend
7. ⬜ Add WebSocket streaming
8. ⬜ Create `bugninja platform` CLI command
9. ⬜ Package frontend build with Python package
10. ⬜ Documentation and examples

## Notes

- **No SQLite, no PostgreSQL, no ORM** - just file I/O
- **In-memory caching** can be added later with Python's `@lru_cache` if needed
- **File watching** with `watchdog` library for real-time UI updates
- **CORS** must be configured for local development
- **Static file serving** for built React app in production mode

