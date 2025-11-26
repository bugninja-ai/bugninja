# Frontend Adaptation Plan - Single Project Mode

## Overview
Converting the multi-project frontend to work with the single-project file-based backend.

## Key Changes Required

### 1. Project Context (HIGH PRIORITY)
**File**: `src/app/providers/ProjectContext.tsx`
- Remove multi-project logic
- Fetch single project from `/api/v1/project`
- Remove project selection/switching UI
- Auto-load the current project on mount

### 2. Project Service (HIGH PRIORITY)
**File**: `src/features/projects/services/projectService.ts`
- Change endpoint from `/projects/` to `/project`
- Remove pagination logic
- Simplify to single project GET/PUT operations
- Remove create/delete project methods

### 3. Navigation Sidebar (MEDIUM PRIORITY)
**File**: `src/shared/components/NavigationSidebar.tsx`
- Remove project dropdown component
- Show static project name from context
- Remove project switching UI

### 4. Settings Page (MEDIUM PRIORITY)
**File**: `src/features/settings/SettingsPage.tsx`
- Remove "Projects" section from settings
- Keep only project name/URL editing
- Remove project deletion
- Remove project creation modal

### 5. API Base Configuration (HIGH PRIORITY)
**File**: `src/shared/services/api.ts`
- Verify base URL matches backend (currently `localhost:8000`)
- No changes needed if backend runs on same port

### 6. Test Case Service (LOW PRIORITY)
**File**: `src/features/test-cases/services/testCaseService.ts`
- Remove `project_id` from API calls if present
- Update endpoints to match backend structure

### 7. Layout Component (MEDIUM PRIORITY)
**File**: `src/app/layout/Layout.tsx`
- Remove project creation triggers
- Simplify header to show single project

## Implementation Order

1. ✅ **ProjectContext** - Core change, affects everything
2. ✅ **ProjectService** - Required by context
3. ✅ **NavigationSidebar** - Remove project switcher
4. ✅ **Settings** - Simplify project settings
5. ✅ **Layout** - Remove project creation UI
6. ⚠️ **Test all pages** - Verify no project-related errors

## API Endpoint Mapping

### Old (Multi-project)
- `GET /projects/` - List all projects
- `GET /projects/{id}` - Get project
- `POST /projects/` - Create project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project

### New (Single-project)
- `GET /api/v1/project` - Get current project
- `PUT /api/v1/project` - Update current project

## Testing Checklist

- [ ] Project loads automatically
- [ ] Project name displays correctly
- [ ] Settings can update project info
- [ ] Test cases list works
- [ ] Test execution works
- [ ] Test runs display works
- [ ] No console errors about missing projects

