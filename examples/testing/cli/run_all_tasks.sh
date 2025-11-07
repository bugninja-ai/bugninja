#!/bin/bash

# Run all Bugninja tasks sequentially
# This script executes all tasks in the correct order, respecting dependencies

echo "Starting sequential execution of all Bugninja tasks..."
echo "=================================================="

# Task 1: Simple Navigation
echo "Running Task 1: Simple Navigation..."
uv run bugninja run 1_simple_navigation
echo "Task 1 completed."
echo ""

# Task 2: Simple Navigation with Replay
echo "Running Task 2: Simple Navigation with Replay..."
uv run bugninja run 2_simple_navigation_with_replay
echo "Task 2 completed."
echo ""

# Task 3: Mobile Viewport
echo "Running Task 3: Mobile Viewport..."
uv run bugninja run 3_mobile_viewport
echo "Task 3 completed."
echo ""

# Task 4: Self Healing
echo "Running Task 4: Self Healing..."
uv run bugninja run 4_self_healing
echo "Task 4 completed."
echo ""

# Task 5: Secrets
echo "Running Task 5: Secrets..."
uv run bugninja run 5_secrets
echo "Task 5 completed."
echo ""

# Task 6: Extra Instructions Navigation
echo "Running Task 6: Extra Instructions Navigation..."
uv run bugninja run 6_extra_instructions_navigation
echo "Task 6 completed."
echo ""

# Task 7: Secrets Scrolling Replay
echo "Running Task 7: Secrets Scrolling Replay..."
uv run bugninja run 7_secrets_scrolling_replay
echo "Task 7 completed."
echo ""

# Task 8: Comprehensive Test
echo "Running Task 8: Comprehensive Test..."
uv run bugninja run 8_comprehensive_test
echo "Task 8 completed."
echo ""

# Task 9: TODO List Creation
echo "Running Task 9: TODO List Creation..."
uv run bugninja run 9_todolist_creation
echo "Task 9 completed."
echo ""

# Task 9b: TODO List Deletion
echo "Running Task 9b: TODO List Deletion..."
uv run bugninja run 9_todolist_deletion
echo "Task 9b completed."
echo ""

# Task 10: File Upload
echo "Running Task 10: File Upload..."
uv run bugninja run 10_file_upload
echo "Task 10 completed."
echo ""

# Task 11: HTTP Authentication
echo "Running Task 11: HTTP Authentication..."
uv run bugninja run 11_http_authentication
echo "Task 11 completed."
echo ""

# Task 12: Failing Test Case
echo "Running Task 12: Failing Test Case..."
uv run bugninja run 12_failing_testcase
echo "Task 12 completed."
echo ""

echo "=================================================="
echo "All tasks completed successfully!"
echo "Check the individual task outputs above for results."
