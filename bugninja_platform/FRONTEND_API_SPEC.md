# Frontend API Specification

This document describes the expected API structure based on the existing frontend implementation.

## Test Execution Flow

### 1. Execute Test Endpoint

**Frontend Call:**
```typescript
POST /test-runs/execute-configuration/{testCaseId}/{browserConfigId}
```

**Response (immediate):**
```json
{
  "id": "run_xyz123",  // Test run ID
  ... (full test run object)
}
```

### 2. Get Test Run Details (Polling)

**Frontend Call:**
```typescript
GET /test-runs/{runId}
```

**Response Structure:**
```json
{
  "id": "run_xyz123",
  "test_case": {
    "id": "task_id",
    "test_name": "Task Name",
    "test_description": "Description",
    "test_goal": "Goal"
  },
  "current_state": "RUNNING" | "FINISHED" | "FAILED" | "ERROR" | "PENDING",
  "started_at": "2025-11-12T12:00:00Z",
  "finished_at": "2025-11-12T12:05:00Z" | null,
  "run_type": "AGENTIC" | "REPLAY" | "REPLAY_WITH_HEALING",
  "origin": "WEB_UI" | "CI/CD",
  "browser_config": {
    "id": "browser_config_id",
    "browser_config": {
      "user_agent": "Mozilla/5.0...",
      "viewport": {
        "width": 1920,
        "height": 1080
      },
      "geolocation": {
        "latitude": 40.7128,
        "longitude": -74.0060
      }
    }
  },
  "brain_states": [
    {
      "id": "state_1",
      "evaluation_previous_goal": "Successfully logged in",
      "next_goal": "Navigate to dashboard",
      "memory": "User is authenticated",
      "history_elements": [
        {
          "id": "action_1",
          "history_element_state": "SUCCESS" | "FAILED",
          "action": {
            "go_to_url": { "url": "https://example.com" },
            // OR
            "input_text": { "text": "username", "index": 0 },
            // OR
            "click_element_by_index": { "index": 0 },
            // OR
            "done": { "text": "Task completed successfully" }
          },
          "screenshot": "https://server/screenshots/001.png",
          "dom_element_data": {
            "xpath": "//input[@id='username']"
          }
        }
      ]
    }
  ],
  "run_gif": "https://server/videos/run.gif" | null,
  "test_traversal_id": "traversal_id"
}
```

## Polling Strategy

### Frontend Implementation

1. **Execute test** - POST to execute endpoint
2. **Get run ID** from response
3. **Navigate** to `/runs/{runId}`
4. **Start polling** every 3 seconds
5. **Check status** - if `current_state` is NOT `"RUNNING"` or `"PENDING"`, stop polling
6. **Auto-scroll** to bottom on each update

### Status Mapping

```typescript
const statusMap = {
  'RUNNING': 'pending',
  'PENDING': 'pending',
  'FINISHED': 'passed',
  'PASSED': 'passed',
  'FAILED': 'failed',
  'ERROR': 'failed'
}
```

## Key Data Structures

### Brain State
- Represents one "thinking step" of the AI
- Contains:
  - Evaluation of previous goal
  - Next goal to achieve
  - Memory/context
  - List of actions taken

### History Element (Action)
- Specific action within a brain state
- Types:
  - `go_to_url` - Navigation
  - `input_text` - Form filling (can contain `<secret>NAME</secret>`)
  - `click_element_by_index` - Click action
  - `done` - Test completion
- Each has:
  - Status (SUCCESS/FAILED)
  - Screenshot
  - XPath (for input/click actions)

### Test Run States
- `PENDING` - Not started yet
- `RUNNING` - Currently executing
- `FINISHED` - Completed successfully
- `PASSED` - Same as FINISHED
- `FAILED` - Test failed
- `ERROR` - System error

## Implementation Notes

1. **Secrets Handling**: 
   - Frontend detects `<secret>SECRET_NAME</secret>` in input_text
   - Displays as "Fill password/secret input"
   - Shows secret name, not value

2. **Screenshots**:
   - Each action can have a screenshot URL
   - Frontend shows modal on click
   - Base domain: `http://localhost:8000`

3. **Browser Detection**:
   - Parsed from user_agent string
   - Chrome, Safari, Firefox, Edge supported

4. **GIF Support**:
   - Optional `run_gif` field
   - Displayed if available

5. **Real-time Updates**:
   - Poll every 3 seconds while `RUNNING`
   - Auto-scroll to latest action
   - Stop polling when completed



