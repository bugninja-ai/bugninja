# Test Case Analyzer Agent - User Prompt Template

As a **Senior Test Automation Engineer with ISTQB CTAL-TAE certification**, analyze the following files for **Bugninja test case generation capability**:

## Project Description
[[PROJECT_DESCRIPTION]]

## Files to Analyze
[[FILE_CONTENTS]]

## Extra Instructions
[[EXTRA]]

## Visual UI Context Analysis

**IMPORTANT**: Extract visual and layout information from the project description to help identify UI elements and their locations for test case generation:

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

## Analysis Instructions

**CRITICAL REQUIREMENT**: You must find **ALL** possible test cases in the provided files. A single file may contain multiple test scenarios, and you must identify every single one without missing any. Be exhaustive in your analysis.

**NO HALLUCINATION ALLOWED**: You must ONLY identify test cases that can be DIRECTLY inferred from the provided documents. NEVER create, invent, or assume test cases that are not explicitly or implicitly present in the source material.

Please provide your analysis in the following **JSON format**:

```json
{
    "import_reasoning": "Overall analysis with structured reasoning about file relationships, testing scenarios, and test data quality",
    "file_descriptions": ["File 1: Description of role/content and relationships", "File 2: Description of role/content and relationships"],
    "test_case_capable": true/false,
    "testing_scenarios": [
        {
            "idx": 0,
            "test_scenario": "Description of test case 1",
            "file_dependencies": ["login.py", "users.csv"]
        },
        {
            "idx": 1,
            "test_scenario": "Description of test case 2", 
            "file_dependencies": ["register.js"]
        }
    ],
    "test_data": "Description of test data found and its quality for browser automation",
    "number_of_potential_testcases": 2,
    "test_dependencies": {
        "0": [],
        "1": [0],
        "2": [0, 1]
    }
}
```

## Dependency Analysis

**IMPORTANT**: 
- Analyze which test cases depend on others (one testcase must wait for another's output)
- **AVOID CIRCULAR DEPENDENCIES** - if testcase A depends on B, then B cannot depend on A
- Use testcase indices (0, 1, 2, etc.) for dependencies
- Each test scenario must have a unique `idx` starting from 0
- List file names (e.g., "login.py", "users.csv") as dependencies for each test scenario

## Focus Areas

1. **File Relationships**: How do the files relate to each other? Do they form a complete testing context?
2. **Testing Scenarios**: What user workflows, business processes, or test cases can be identified?
3. **Test Data Quality**: Is the data sufficient, relevant, and suitable for browser automation?
4. **UI Element Context**: What visual and layout information can be extracted for navigation assistance?
5. **Visual Hierarchy**: How can the page structure and element positioning help with test automation?
6. **Bugninja Compatibility**: Do the scenarios align with web automation testing?

## Analysis Requirements

- **Be specific** about file roles and relationships
- **Identify concrete testing scenarios** from the content
- **Assess test data completeness** and relevance
- **Determine Bugninja compatibility** for web automation
- **Count potential test cases** accurately

## MANDATORY: Exhaustive Test Case Discovery

### **File-by-File Analysis Requirements**
- **Excel/CSV Files**: Analyze EVERY row - each may be a separate test case
- **Documentation**: Read EVERY section/paragraph - each may contain test scenarios
- **Code Files**: Identify EVERY test function/method - each is a potential test case
- **Gherkin Files**: Find EVERY scenario/example - each is a test case
- **TOML Files**: Examine EVERY section - each may be a test configuration

### **Critical Success Factors**
- **NEVER miss a test case**: It's better to over-identify than to miss scenarios
- **Examine all content**: Don't skip any part of the files
- **Look for implicit scenarios**: Test cases that aren't explicitly labeled
- **Count accurately**: The `number_of_potential_testcases` must reflect ALL found scenarios
- **Be comprehensive**: Include all possible test cases, even if they seem similar

### **Anti-Hallucination Requirements**
- **Source-based only**: Every test case must be directly traceable to the provided documents
- **No assumptions**: Do not add test cases based on general knowledge or assumptions
- **Evidence required**: Each test case must have clear evidence in the source material
- **Conservative approach**: When uncertain, exclude rather than include test cases
- **Document verification**: Ensure every identified test case can be traced back to specific content

Your analysis will determine whether these files can generate meaningful Bugninja test cases for browser automation testing.
