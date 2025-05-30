# AI Web Navigation Agent - Design Document V1

## Overview

This document outlines the design approach for building an AI-powered web navigation agent that can autonomously browse websites while logging all actions for playback functionality. The agent is designed to overcome the six major technical limitations identified in current AI browsing/testing agents.

## Problem Statement

### Core Issues with Current AI Web Agents

Based on our analysis, AI web navigation faces six critical limitations (ranked by difficulty):

1. **Browser Context Interpretation** (Hardest)
   - Difficulty determining which window/popup to focus on
   - Popups and modals create confusion
   - Loading times are hard to interpret algorithmically

2. **Meaningless Loops** - Lack of QA mindset
   - Agents often lose their original goal
   - Get trapped in circular navigation patterns

3. **Soft Interactions**
   - Cannot efficiently emulate dynamic interactions (hovering + scrolling simultaneously)

4. **Atomic Interactions**
   - Without proper context, AI struggles with generic interfaces
   - Needs detailed element information and context

5. **Hallucinations**
   - AI falsely believes it completed goals
   - Loses track of original objectives with large context
   - Fills wrong form fields

6. **Complex Feature Behavior** (Easiest)
   - Product-specific business logic is hard to interpret
   - Complex calculations and workflows

## Solution Architecture

### Core Principles

1. **Break down to atomic interactions** - Every action should be the most basic possible (click, type, scroll, key_press)
2. **State-based navigation graph** - Each action creates a new state for reproducibility
3. **Comprehensive logging** - Full state capture for playback without AI
4. **Failure management** - Multiple retry strategies like human users
5. **Context-aware element extraction** - Rich element information for AI decision making

## Operating Modes

### Goal-Oriented Mode
Traditional test automation where the agent follows specific test cases or user stories:
- **Input**: Specific task description ("Fill out contact form and submit")
- **Behavior**: Focused navigation toward completing the defined goal
- **Success**: Task completion with minimal steps
- **Use Case**: Regression testing, specific workflow validation

### Exploration Mode
Comprehensive site exploration like a QA engineer discovering functionality:
- **Input**: Site URL and exploration parameters (depth, coverage targets)
- **Behavior**: Systematic discovery of all interactive elements and paths
- **Success**: Maximum coverage of site functionality and paths
- **Use Case**: Site mapping, feature discovery, comprehensive testing

### Exploration Strategy

**Coverage-Driven Exploration:**
```json
{
  "exploration_state": {
    "visited_urls": ["url1", "url2", ...],
    "discovered_elements": {
      "buttons": ["signup", "login", "checkout", ...],
      "forms": ["contact", "registration", ...],
      "navigation": ["menu", "footer_links", ...]
    },
    "functionality_map": {
      "authentication": ["login", "signup", "logout"],
      "ecommerce": ["add_to_cart", "checkout", "payment"],
      "content": ["search", "filter", "pagination"]
    },
    "coverage_metrics": {
      "elements_interacted": 45,
      "total_elements_found": 120,
      "coverage_percentage": 37.5,
      "unique_pages_visited": 8
    }
  }
}
```

**Exploration Behaviors:**

1. **Breadth-First Discovery**:
   - Find all interactive elements on current page
   - Try each element once before going deeper
   - Map out site structure level by level

2. **Depth-First Investigation**:
   - Follow interesting paths to completion
   - Useful for discovering complete workflows
   - Good for finding edge cases in specific features

3. **Random Walk Simulation**:
   - Mimic human browsing patterns
   - Weight decisions based on element visibility/prominence
   - Include realistic pauses and backtracking

**Exploration AI Prompting:**
```python
exploration_prompt = f"""
You are a QA engineer exploring a website to discover all functionality.

Current page elements: {element_list}
Already explored: {visited_elements}
Coverage so far: {coverage_percentage}%

Goal: Discover new functionality and map site capabilities.

Choose an element to interact with that:
1. Haven't explored yet (priority)
2. Might lead to new functionality
3. Represents common user behavior

Reasoning: Explain why this element is interesting to explore.
"""
```

**Coverage Tracking:**
- **Element Coverage**: Track which interactive elements have been tested
- **Path Coverage**: Map different routes through the site
- **Functionality Coverage**: Categorize discovered features
- **Dead End Detection**: Identify non-functional or broken elements
- **Loop Prevention**: Avoid infinite cycles while allowing legitimate revisits

## Two-Phase Architecture: Exploration → Execution

### The Core Innovation

Our architecture creates a **comprehensive site graph** through exploration that enables **AI-free test execution**:

1. **Phase 1 - Exploration (AI-Driven)**: Map the entire site functionality
2. **Phase 2 - Execution (Deterministic)**: Follow pre-discovered paths for testing

### Exploration Phase Details

**Boundary Conditions:**
- **Maximum step count**: Configurable limit (e.g., 1000 actions) to prevent infinite exploration
- **Dead end detection**: AI determines when no new functionality can be discovered
- **Coverage threshold**: Stop when X% of elements have been explored
- **Time limits**: Maximum exploration duration

**Dead End Detection Logic:**
```python
def is_dead_end(current_state, exploration_history):
    """
    Determine if exploration has reached a dead end
    """
    criteria = {
        "no_new_elements": len(current_state.new_elements) == 0,
        "all_paths_explored": all_available_actions_tried(current_state),
        "step_limit_reached": len(exploration_history) >= MAX_STEPS,
        "circular_navigation": detect_loops(exploration_history, depth=10)
    }
    return any(criteria.values())
```

### Graph-Based Test Generation

**Complete Site Map Structure:**
```json
{
  "site_graph": {
    "nodes": {
      "homepage": {
        "url": "https://shop.com/",
        "elements": [...],
        "screenshot": "screenshots/homepage.png"
      },
      "product_page": {
        "url": "https://shop.com/product/123",
        "elements": [...],
        "screenshot": "screenshots/product.png"
      }
    },
    "edges": {
      "homepage_to_product": {
        "action": {"type": "click", "target": "product_link"},
        "success_rate": 1.0,
        "avg_load_time": 1.2
      }
    },
    "workflows": {
      "checkout_flow": {
        "path": ["homepage", "product_page", "cart", "checkout", "payment"],
        "actions": [
          {"state": "homepage", "action": "click", "target": "product_link"},
          {"state": "product_page", "action": "click", "target": "add_to_cart"},
          {"state": "cart", "action": "click", "target": "checkout_btn"},
          {"state": "checkout", "action": "type", "target": "email_field", "value": "test@example.com"},
          {"state": "payment", "action": "click", "target": "pay_btn"}
        ],
        "test_data_required": ["email", "address", "payment_info"]
      }
    }
  }
}
```

### AI-Free Test Execution

**Automatic Test Case Generation:**
```python
def generate_test_cases_from_graph(site_graph, test_scenarios):
    """
    Extract test cases from exploration graph
    """
    test_cases = []
    
    for scenario in test_scenarios:
        if scenario == "checkout_flow":
            # Extract exact path from graph
            path = site_graph.workflows.checkout_flow.path
            actions = site_graph.workflows.checkout_flow.actions
            
            test_case = {
                "name": "checkout_flow_test",
                "steps": actions,
                "expected_states": path,
                "requires_ai": False  # Pure path following
            }
            test_cases.append(test_case)
    
    return test_cases
```

**Deterministic Execution:**
- **No AI needed**: Just follow the pre-mapped action sequence
- **Fast execution**: No decision-making overhead
- **Reliable results**: Known working paths from exploration
- **Parallel testing**: Multiple paths can run simultaneously

**Path Selection Strategies:**
- **Manual selection**: Choose specific workflows to test
- **Random path algorithms**: Randomly select valid paths for coverage
- **Risk-based selection**: Prioritize critical business flows
- **Regression testing**: Re-run previously working paths

### Benefits of This Architecture

1. **Separation of Concerns**:
   - Exploration: AI discovers and maps (one-time cost)
   - Execution: Deterministic following (repeatable, fast)

2. **Efficiency**:
   - Exploration cost amortized across many test runs
   - Test execution becomes lightweight
   - Can run tests without AI model costs

3. **Reliability**:
   - Tests follow proven working paths
   - Reduced flakiness from AI decision variability
   - Exact reproducibility

4. **Scalability**:
   - Once mapped, unlimited test execution
   - Easy to generate comprehensive test suites
   - Parallel execution of different paths

### State Representation

Each state in our navigation graph contains:

```json
{
  "state_id": "uuid",
  "screenshot_path": "screenshots/state_123.png",
  "available_elements": [
    {
      "id": "element_uuid",
      "selector": "button[data-testid='submit']",
      "xpath": "//button[@data-testid='submit']",
      "coordinates": [150, 300],
      "text": "Submit Form",
      "role": "button",
      "bbox": [100, 250, 200, 350],
      "is_visible": true,
      "is_enabled": true
    }
  ],
  "task_context": "Fill out contact form and submit",
  "ai_reasoning": "User wants to submit form, I should click the submit button",
  "action_taken": {
    "type": "click",
    "target_element": "element_uuid",
    "success": true,
    "retry_attempts": [
      {"method": "css_selector", "success": false},
      {"method": "xpath", "success": true}
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "next_state_id": "next_uuid"
}
```

### Atomic Interaction Types

All complex actions are broken down into these primitives:

- `click(element_id)` - Single click on identified element
- `type(text)` - Type text into currently focused element
- `scroll(direction, amount)` - Scroll in specified direction
- `key_press(key)` - Press specific keys (Enter, Tab, Escape, etc.)
- `hover(element_id)` - Hover over element
- `wait(condition)` - Wait for loading, element appearance, etc.
- `go_to_url(url)` - Navigate to specific URL

**Example: Dropdown Selection Breakdown**
Instead of `select_dropdown_option()`, we use:
1. `click(dropdown_element)`
2. `wait(dropdown_open)`
3. `scroll(down, 2)` (if needed)
4. `click(option_element)`

### Element Identification Strategy

**Hybrid Approach for Maximum Reliability:**

1. **Primary**: CSS Selectors (fast, reliable when available)
2. **Fallback**: XPath (more flexible for complex relationships)
3. **Last Resort**: Coordinates (brittle but universal)
4. **Validation**: Text content and accessibility roles

### Element Extraction Process

1. **Use Patchright's locator system** to find all interactive elements:
   - Buttons, links, inputs, selects
   - Elements with click handlers
   - Role-based identification

2. **Extract comprehensive element data**:
   - Multiple selector types for reliability
   - Visual information (coordinates, bounding box)
   - Semantic information (text, role, state)

3. **Create annotated screenshots**:
   - Overlay bounding boxes on interactive elements
   - Number or label elements for AI reference
   - Maintain visual context

## Technical Stack

### Core Technologies

- **[Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python)**: Undetectable Playwright wrapper
  - Passes major bot detection (Cloudflare, Kasada, etc.)
  - Same API as Playwright with stealth enhancements
  - Closed shadow root support

- **Azure OpenAI**: AI reasoning and decision making
  - GPT-4V for vision-based element analysis
  - Text models for action planning and reasoning
  - Available credits through existing account

- **Python**: Primary development language
  - Async/await for browser automation
  - Rich ecosystem for image processing and AI integration

### Browser Configuration

```python
# Recommended undetectable setup
browser = await patchright.chromium.launch_persistent_context(
    user_data_dir="./browser_data",
    channel="chrome",  # Use real Chrome, not Chromium
    headless=False,
    no_viewport=True,
    # No custom headers or user agents for maximum stealth
)
```

## AI Integration Strategy

### Decision Making Flow

1. **Input to AI**:
   - Current task/goal description
   - List of available interactive elements
   - Annotated screenshot
   - Previous action history (for context)

2. **AI Output**:
   - Selected atomic action type
   - Target element identification
   - Reasoning for the choice
   - Confidence level

3. **Action Execution**:
   - Attempt primary method (CSS selector)
   - Fallback methods if primary fails
   - Log all attempts for learning

### Prompt Structure

```python
prompt = f"""
Task: {task_description}

Available Actions: click, type, scroll, hover, key_press, wait, go_to_url

Current Page Elements:
{formatted_element_list}

Previous Actions: {action_history}

Choose the next atomic action and provide reasoning.
Format: {{"action": "click", "target": "element_id", "reasoning": "explanation"}}
"""
```

## Failure Management & Recovery

### Retry Strategy

When an action fails:
1. **Log the failure** with method attempted
2. **Try alternative identification methods**:
   - CSS selector → XPath → Coordinates
3. **Try alternative interaction approaches**:
   - Click → Key press (if focused) → JavaScript click
4. **Wait and retry** (for timing issues)
5. **Mark as failed** if all methods exhausted

### Success Criteria

- **Action Success**: Browser state changed as expected
- **Goal Progress**: Moving closer to overall task completion
- **Element Interaction**: Successfully interacted with intended element

## Navigation Graph Structure

### Graph Properties

- **Directional**: Actions have specific start/end states
- **Cyclical**: Loops and cycles are acceptable
- **Branching**: Multiple paths to achieve goals
- **Prunable**: Failed paths can be excluded from replay

### State Transitions

Every atomic action creates a new state:
- Screenshot captures visual state
- Element list captures interaction possibilities
- Action log captures what changed

### Playback Mechanism

Saved states allow for:
- **Exact reproduction** of successful paths
- **Alternative path exploration** from any state
- **Human verification** of agent decisions
- **Training data** for improving the AI

## Future Considerations

### Version 1 Limitations

- Focus on single-page interactions initially
- Limited popup/modal handling
- Basic error recovery
- Manual task definition

### Planned Enhancements

- **Multi-tab/window management**
- **Advanced context switching**
- **Dynamic goal adjustment**
- **Learning from failure patterns**
- **Integration with testing frameworks**

## Implementation Phases

### Phase 1: Core Infrastructure
- Basic element extraction
- Screenshot annotation
- State management
- Simple AI integration

### Phase 2: Atomic Actions
- Implement all atomic interaction types
- Retry mechanisms
- Action logging

### Phase 3: AI Decision Making
- Azure OpenAI integration
- Prompt optimization for goal-oriented mode
- Decision quality metrics

### Phase 4: Graph Management
- State persistence
- Playback functionality
- Path optimization

### Phase 5: Exploration Mode
- Coverage tracking system
- Exploration algorithms (breadth-first, depth-first, random walk)
- Functionality categorization and mapping
- Exploration-specific AI prompting

## Success Metrics

**Goal-Oriented Mode:**
- **Reliability**: Consistent element identification across sessions
- **Completeness**: Successfully completing defined tasks
- **Efficiency**: Task completion with minimal steps
- **Reproducibility**: Playback accuracy of logged sessions
- **Stealth**: Avoiding bot detection on target sites
- **Recovery**: Graceful handling of failed actions

**Exploration Mode:**
- **Coverage**: Percentage of interactive elements discovered and tested
- **Discovery**: Number of unique functionalities and workflows found
- **Mapping**: Completeness of site structure and feature categorization
- **Edge Case Detection**: Identification of broken links, errors, or unusual behaviors
- **Efficiency**: Coverage achieved per time unit
- **Depth**: Average and maximum navigation depth reached

---

*This document represents Version 1 of our design approach and will be updated as we learn from implementation and testing.* 