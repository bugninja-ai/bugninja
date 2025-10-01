# Test Case Generator Agent - User Prompt Template

As a **Senior Test Automation Engineer with ISTQB CTAL-TAE certification**, generate **production-quality Bugninja test cases** from the following project description using professional test case design principles:

## Project Description
[[PROJECT_DESCRIPTION]]

## Generation Requirements
- **Number of Test Cases**: [[N]]
- **Test Distribution**: [[TEST_DISTRIBUTION_INFO]]
- **Extra Instructions**: [[EXTRA]]

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

Apply your **CTAL-TAE expertise** and generate a complete set of production-quality Bugninja test cases in the following **JSON format**:

```json
[
    {
        "task_name": "Descriptive name for test case 1",
        "description": "Clear description of what the test case does and its purpose",
        "extra_instructions": [
            "Step 1: Navigate to the application",
            "Step 2: Perform specific actions",
            "Step 3: Validate expected outcomes"
        ],
        "secrets": {
            "KEY_NAME": "test_value_if_needed"
        }
    },
    {
        "task_name": "Descriptive name for test case 2",
        "description": "Clear description of what the test case does and its purpose",
        "extra_instructions": [
            "Step 1: Navigate to the application",
            "Step 2: Perform specific actions",
            "Step 3: Validate expected outcomes"
        ],
        "secrets": {
            "KEY_NAME": "test_value_if_needed"
        }
    }
]
```

## Key Requirements

### **Test Case Distribution**
- **Positive Test Cases**: Normal user workflows and expected behaviors
- **Negative Test Cases**: Error scenarios, edge cases, and failure conditions
- **Independent Test Cases**: Each test case should be executable independently
- **Unique Names**: Avoid naming conflicts between generated test cases

### **Test Case Naming**
- **Descriptive Names**: Clear, specific names that reflect the test purpose
- **Conflict Avoidance**: Use incremental numbering or unique identifiers
- **Professional Standards**: Follow naming conventions for enterprise test automation

### **Test Case Content**
- **Complete Workflows**: Full user journeys from start to finish
- **Validation Steps**: Clear checks for expected outcomes
- **Error Handling**: Appropriate error scenarios and recovery steps
- **Realistic Data**: Use realistic test data and scenarios

### **Positive Test Cases**
Focus on:
- **Happy Path Scenarios**: Normal user workflows
- **Core Functionality**: Primary application features
- **User Journeys**: Complete end-to-end processes
- **Business Logic**: Critical application workflows

### **Negative Test Cases**
Focus on:
- **Input Validation**: Invalid data entry scenarios
- **Authentication Failures**: Login/security error cases
- **Boundary Conditions**: Edge cases and limits
- **System Errors**: Network, server, and application failures

## Instruction Writing Guidelines

### **Clear and Actionable**
- Use imperative mood ("Click the button", "Enter the username")
- Be specific about UI elements with location context ("Click the 'Login' button in the top-right corner", "Enter text in the 'Email' field in the login form")
- Include navigation steps with visual context ("Navigate to the homepage", "Go to the settings page via the user menu")
- Add visual positioning clues ("Click the blue 'Submit' button at the bottom of the form", "Select from the dropdown menu in the sidebar")

### **Logical Flow**
- Start with navigation to the application
- Follow the natural user workflow
- Include validation steps at appropriate points
- End with cleanup or logout if needed

### **Validation Steps**
- Include checks for expected outcomes with visual context ("Verify the success message appears in the green notification bar", "Confirm the user avatar is displayed in the top-right corner")
- Verify UI state changes with location details ("Check that the 'Edit' button changes to 'Save' in the form header", "Confirm the loading spinner appears in the center of the page")
- Confirm data appears correctly with positioning ("Verify the product list updates in the main content area", "Check that the total price is displayed in the checkout summary")
- Check for error messages when appropriate with visual cues ("Look for red error text below the form fields", "Verify the warning message appears in the yellow alert box")

### **Error Scenarios**
- Consider what could go wrong
- Include steps to handle common errors
- Provide fallback actions when possible

## Quality Standards

### **Completeness**
- Cover entire user workflows from start to finish
- Include all necessary steps for execution
- Provide sufficient detail for AI agents to understand
- Ensure test cases are independent and executable

### **Accuracy**
- Base test cases on realistic user scenarios
- Use appropriate test data and conditions
- Follow application domain best practices
- Consider real-world usage patterns

### **Clarity**
- Write instructions that are easy to follow
- Use consistent terminology and naming
- Be specific about UI elements and actions
- Provide clear validation criteria

### **Professionalism**
- Follow enterprise test automation standards
- Ensure maintainability and reusability
- Consider scalability and performance
- Apply risk-based testing principles

## Important Notes

- **Be comprehensive**: Cover both positive and negative scenarios
- **Be realistic**: Use realistic test data and scenarios
- **Be independent**: Ensure test cases can run independently
- **Be clear**: Write instructions that are easy to understand
- **Be professional**: Follow enterprise testing standards

Your generated test cases will be converted into Bugninja TOML files and can be executed immediately for comprehensive browser automation testing.
