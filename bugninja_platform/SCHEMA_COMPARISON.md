# Schema Comparison: Current vs Frontend Expected

## ❌ Issues Found

### 1. Task/Test Case Schema Mismatch

#### What We're Currently Returning (Task):
```json
{
  "id": "1_simple_navigation",
  "name": "1_simple_navigation",
  "description": "Login to the platform...",
  "start_url": "https://app.bacprep.ro/en",
  "folder_name": "1_simple_navigation",
  "toml_path": "/path/to/task.toml",
  "created_date": "2025-10-09T17:01:12...",
  "extra_instructions": [],
  "dependencies": [],
  "allowed_domains": [],
  "task_id": "eyfhemjm3ea2oblgx3bnou3h"
}
```

#### What Frontend Expects (BackendTestCase):
```typescript
{
  id: string;
  project_id: string;                    // ❌ MISSING
  document: BackendDocument | null;       // ❌ MISSING
  browser_configs: BackendBrowserConfig[]; // ❌ MISSING
  secrets: BackendSecretValue[];         // ❌ MISSING
  created_at: string;                     // ✅ Have as "created_date"
  updated_at: string;                     // ❌ MISSING
  test_name: string;                      // ✅ Have as "name"
  test_description: string;               // ✅ Have as "description"
  test_goal: string;                      // ❌ MISSING (in TOML but not extracted)
  extra_rules: string[];                  // ✅ Have as "extra_instructions"
  url_routes: string;                     // ✅ Have as "start_url"
  url_route?: string;                     // Same as above
  allowed_domains: string[];              // ✅ Have
  priority: 'low' | 'medium' | 'high' | 'critical';  // ❌ MISSING
  category: string | null;                // ❌ MISSING
  total_runs: number;                     // ❌ MISSING (need to calculate)
  passed_runs: number;                    // ❌ MISSING (need to calculate)
  failed_runs: number;                    // ❌ MISSING (need to calculate)
  pending_runs: number;                   // ❌ MISSING (need to calculate)
  success_rate: number;                   // ❌ MISSING (need to calculate)
  last_run_at: string | null;            // ❌ MISSING (need to calculate)
}
```

### 2. Project Schema

#### What We're Currently Returning:
```json
{
  "id": "cli",
  "name": "test_init",
  "default_start_url": "",
  "created_at": 1758876779.8639932,      // ❌ Unix timestamp, not ISO string
  "updated_at": 1758876779.8640234,      // ❌ Unix timestamp, not ISO string
  "tasks_dir": "/path/to/tasks",         // ❌ Extra field
  "project_root": "/path/to/project",    // ❌ Extra field
  "config": {...}                         // ❌ Extra field
}
```

#### What Frontend Expects:
```typescript
{
  id: string;                             // ✅ OK
  name: string;                           // ✅ OK
  default_start_url: string;              // ✅ OK
  created_at: string;                     // ❌ Should be ISO string
  updated_at: string;                     // ❌ Should be ISO string
}
```

## ✅ What Needs to be Fixed

### Task Service Updates

1. **Add missing fields from TOML:**
   - `test_goal` - Read from `[task].goal` or description
   - `priority` - Read from `[task].priority` (default: "medium")
   - `category` - Read from `[task].category` (default: null)
   - `project_id` - Use project name or folder name

2. **Calculate run statistics:**
   - Scan `results/{task_name}/` folder for traversal files
   - Count total runs, passed, failed, pending
   - Calculate success_rate percentage
   - Get last_run_at from most recent file

3. **Browser configs:**
   - Read from `[run_config]` section
   - Transform to BackendBrowserConfig format
   - Generate ID for each config

4. **Secrets:**
   - Read from `.env` file or TOML
   - Need to determine which secrets are used by this task
   - Transform to BackendSecretValue format

5. **Field name mapping:**
   - `name` → `test_name`
   - `description` → `test_description`
   - `start_url` → `url_routes`
   - `extra_instructions` → `extra_rules`
   - `created_date` → `created_at`

### Project Service Updates

1. **Convert timestamps to ISO strings:**
   ```python
   from datetime import datetime
   created_at = datetime.fromtimestamp(stats.st_birthtime).isoformat()
   updated_at = datetime.fromtimestamp(stats.st_mtime).isoformat()
   ```

2. **Remove extra fields** (or keep for internal use):
   - Keep response minimal, matching frontend expectations
   - Extra fields won't break frontend but aren't needed

## Priority Fixes

### High Priority (Required for frontend to work):
1. ✅ Convert project timestamps to ISO strings
2. ✅ Add `test_goal` field to tasks
3. ✅ Add `priority` field to tasks  
4. ✅ Calculate run statistics (total_runs, passed_runs, etc.)
5. ✅ Add `project_id` field to tasks

### Medium Priority (Needed for full functionality):
6. ✅ Transform browser configs from TOML
7. ✅ Add `updated_at` to tasks
8. ✅ Field name mapping (test_name, test_description, url_routes)

### Low Priority (Nice to have):
9. ⬜ Secrets handling (complex, may skip initially)
10. ⬜ Category support
11. ⬜ Document support

## Recommended Implementation Order

1. **Fix project timestamps** (5 min)
2. **Update task field names and add missing TOML fields** (15 min)
3. **Implement run statistics calculation** (30 min)
4. **Transform browser configs** (20 min)
5. **Test with frontend** (15 min)

Total: ~90 minutes to get frontend working



