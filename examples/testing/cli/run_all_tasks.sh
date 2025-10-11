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

# Task 91: Create TODO List (dependency for task 92)
echo "Running Task 91: Create TODO List..."
uv run bugninja run 91_amazon_book_search
echo "Task 91 completed."
echo ""

# Task 92: Delete TODO Item (depends on task 91)
echo "Running Task 92: Delete TODO Item..."
uv run bugninja run 92_ebay_book_search
echo "Task 92 completed."
echo ""

echo "=================================================="
echo "All tasks completed successfully!"
echo "Check the individual task outputs above for results."
