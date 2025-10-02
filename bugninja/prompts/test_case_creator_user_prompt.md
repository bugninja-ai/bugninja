# Test Case Creator Agent - User Prompt Template

As a **Senior Test Automation Engineer with ISTQB CTAL-TAE certification**, generate a **production-quality Bugninja test case** from the following test scenario and file context using professional test case design principles:

## Test Scenario
[[TEST_SCENARIO]]

## File Dependencies and Context
[[FILE_CONTENTS]]

## Project Description
[[PROJECT_DESCRIPTION]]

## Extra Instructions
[[EXTRA]]

## Visual UI Context Analysis

**IMPORTANT**: Extract visual and layout information from the project description to help the navigation agent locate UI elements:

### **UI Element Location Clues**
- **Navigation Structure**: Identify main navigation menus, breadcrumbs, and page hierarchy
- **Form Layout**: Note form field positions, button locations, and input groupings
- **Content Areas**: Identify main content sections, sidebars, and data display areas
- **Interactive Elements**: Locate clickable buttons, links, dropdowns, and action items
- **Visual Hierarchy**: Understand page layout, header/footer structure, and content flow

### **Element Positioning Context**
- **Relative Positioning**: "Login button in the top-right corner", "Search bar in the header"
- **Section Context**: "Submit button at the bottom of the form", "Navigation menu in the sidebar"
- **Visual Cues**: "Blue 'Add to Cart' button", "Red 'Delete' button in the action column"
- **Layout Patterns**: "Three-column layout with navigation on the left", "Modal dialog in the center"

## Professional Test Case Generation Instructions

Apply your **CTAL-TAE expertise** and generate a complete, production-quality Bugninja test case in the following **JSON format**:

```json
{
    "task_name": "Descriptive name extracted from context or generated based on content",
    "description": "Clear description of what the test case does and its purpose",
    "extra_instructions": [
        "Step 1: Navigate to the application",
        "Step 2: Perform specific actions",
        "Step 3: Validate expected outcomes"
    ],
    "secrets": {
        "KEY_NAME": "value_from_context_if_found"
    }
}
```

## Key Requirements

### **Task Name**
- **Extract from context**: If the files mention a specific test case name, use that
- **Generate from content**: If no name is found, create a descriptive name based on the test scenario
- **Be descriptive**: The name should clearly indicate what the test does

### **Description**
- **Explain the purpose**: What does this test case validate?
- **Include context**: Why is this test important for the application?
- **Be clear**: Write in plain language that explains the test's value

### **Instructions**
- **Step-by-step**: Create clear, actionable instructions with visual context
- **Natural language**: Write as if instructing a human user with location details
- **Specific actions**: Include specific UI interactions with positioning clues (click, type, navigate, scroll)
- **Visual context**: Add location details ("Click the 'Login' button in the top-right corner", "Enter text in the 'Email' field in the login form")
- **Validation steps**: Include checks for expected outcomes with visual positioning
- **Complete workflow**: Cover the entire test scenario from start to finish with UI context

### **Secrets/Test Data**
- **Context-based only**: Only include secrets if they are explicitly found in the provided files
- **No hallucination**: Never invent or assume test data that isn't in the context
- **Realistic values**: Use actual values found in the files
- **Empty if none**: If no test data is found, leave the secrets object empty

## Instruction Writing Guidelines

### **Clear and Actionable**
- Use imperative mood ("Click the button", "Enter the username")
- Be specific about UI elements ("Click the 'Login' button", "Enter text in the 'Email' field")
- Include navigation steps ("Navigate to the homepage", "Go to the settings page")

### **Logical Flow**
- Start with navigation to the application
- Follow the natural user workflow
- Include validation steps at appropriate points
- End with cleanup or logout if needed

### **Validation Steps**
- Include checks for expected outcomes
- Verify UI state changes
- Confirm data appears correctly
- Check for error messages when appropriate

### **Error Scenarios**
- Consider what could go wrong
- Include steps to handle common errors
- Provide fallback actions when possible

## Context Analysis

### **File Content Analysis**
- **Extract test scenarios**: Look for user stories, test cases, or requirements
- **Identify test data**: Find usernames, passwords, API keys, or other test data
- **Understand workflows**: Analyze business processes and user journeys
- **Note dependencies**: Identify relationships between different test steps

### **Test Data Extraction**
- **Look for credentials**: Usernames, passwords, API keys
- **Find test values**: Sample data, test IDs, reference numbers
- **Identify configuration**: Settings, parameters, environment variables
- **Extract URLs**: Test endpoints, application URLs

### **Workflow Understanding**
- **User journeys**: How users interact with the application
- **Business processes**: What the application is supposed to do
- **Validation points**: Where to check for success or failure
- **Edge cases**: Unusual scenarios or error conditions

## Quality Standards

### **Completeness**
- Cover the entire test scenario from start to finish
- Include all necessary steps for execution
- Provide sufficient detail for AI agents to understand

### **Accuracy**
- Base instructions on actual file content
- Use real test data from the context
- Avoid assumptions about functionality not described

### **Clarity**
- Write instructions that are easy to follow
- Use consistent terminology
- Be specific about UI elements and actions

### **Practicality**
- Ensure the test case can be executed
- Include realistic test data
- Consider the application's actual functionality

## Important Notes

- **Be specific**: Extract exact details from the provided context
- **Be realistic**: Use actual test data found in the files
- **Be complete**: Cover the entire test scenario
- **Be clear**: Write instructions that are easy to understand
- **Be accurate**: Base everything on the provided file content

Your generated test case will be converted into a Bugninja TOML file and can be executed immediately for browser automation testing.
