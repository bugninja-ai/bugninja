"""
Azure OpenAI Agent for UI Test Automation
Handles natural language interpretation and selector decision making
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from openai import AsyncAzureOpenAI
from rich.console import Console
from dotenv import load_dotenv

from device_connector import UIElement

# Load environment variables
load_dotenv()

console = Console()


class ActionType(Enum):
    CLICK = "click"
    LONG_CLICK = "long_click"
    SET_TEXT = "set_text"
    CLEAR_TEXT = "clear_text"
    SCROLL = "scroll"
    WAIT = "wait"
    VERIFY = "verify"
    PRESS_ENTER = "press_enter"
    PRESS_BACK = "press_back"


@dataclass
class TestAction:
    """Represents a parsed test action"""

    action_type: ActionType
    target_description: str
    parameters: Dict[str, Any]
    selector_code: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class SelectorDecision:
    """Represents an AI decision for element selection"""

    selected_selector: str
    reasoning: str
    confidence: float
    alternative_selectors: List[str]


class AzureAgent:
    """Azure OpenAI agent for interpreting natural language test instructions"""

    def __init__(self):
        self.client = None
        # Handle deployment name - extract from endpoint if not set
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not self.deployment_name:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            if "/deployments/" in endpoint:
                # Extract deployment name from endpoint
                try:
                    self.deployment_name = endpoint.split("/deployments/")[1].split(
                        "/"
                    )[0]
                except:
                    self.deployment_name = "gpt-4"
            else:
                self.deployment_name = "gpt-4"
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure OpenAI client"""
        try:
            # Support both AZURE_OPENAI_API_KEY and AZURE_OPENAI_KEY
            api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

            if not api_key:
                raise ValueError(
                    "Azure OpenAI API key not found. Set either AZURE_OPENAI_API_KEY or AZURE_OPENAI_KEY"
                )

            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT not found")

            # Ensure endpoint ends with /
            if not endpoint.endswith("/"):
                endpoint += "/"

            self.client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
            console.print("✓ Azure OpenAI client initialized")
            console.print(f"Endpoint: {endpoint}")
            console.print(f"Deployment: {self.deployment_name}")
        except Exception as e:
            console.print(f"✗ Failed to initialize Azure OpenAI client: {str(e)}")
            raise

    async def decide_next_action(
        self,
        goal_instruction: str,
        current_elements: List[UIElement],
        screen_context: str,
        actions_taken: List[TestAction],
        max_steps: int = 30,
    ) -> Optional[TestAction]:
        """Decide the next action to take based on current screen state and goal"""

        elements_formatted = self._format_elements_for_ai(current_elements)

        # Check if the last action was setting text
        last_action_was_text_input = (
            len(actions_taken) > 0
            and actions_taken[-1].action_type == ActionType.SET_TEXT
        )

        system_prompt = f"""You are an expert mobile app testing assistant. Your job is to decide the NEXT SINGLE ACTION to take toward achieving the user's goal.

CONTEXT:
- User Goal: "{goal_instruction}"
- Current screen shows: {screen_context}
- Actions already taken: {len(actions_taken)} steps
- Maximum allowed steps: {max_steps}
- Last action was text input: {last_action_was_text_input}

CURRENT SCREEN ELEMENTS:
{elements_formatted}

Your task is to analyze the current screen and decide what single action to take next to progress toward the goal.

IMPORTANT RULES:
1. If you see a popup, dialog, or permission request, handle it first (dismiss, accept, or interact as needed)
2. If the goal is already achieved, return null to end the test
3. Be flexible - apps may have different flows than expected
4. Handle navigation, search, forms, buttons, and any UI elements you encounter
5. If stuck or can't find relevant elements, try scrolling or going back
6. Always consider the user's ultimate goal, not just the literal instruction

CRITICAL TEXT INPUT WORKFLOW:
- If you just entered text in a search field, URL bar, or input field, you MUST follow up with an appropriate action
- After entering text in search fields: look for search buttons, go buttons, or use press_enter
- After entering text in URL bars: use press_enter to navigate
- After entering text in forms: look for submit buttons or use press_enter
- Don't leave text input hanging without submission - always complete the input workflow

Return a SINGLE action as JSON (MUST be valid JSON). Examples:

For click action:
{{"action_type": "click", "target_description": "search button", "parameters": {{}}, "reasoning": "Need to click search to proceed"}}

For text input:
{{"action_type": "set_text", "target_description": "search field", "parameters": {{"text": "meaning of life"}}, "reasoning": "Enter search query"}}

For submitting after text input:
{{"action_type": "press_enter", "target_description": "search field", "parameters": {{}}, "reasoning": "Submit the search query"}}
{{"action_type": "click", "target_description": "search button", "parameters": {{}}, "reasoning": "Click search button to submit query"}}

Valid action_type values: click, long_click, set_text, clear_text, scroll, wait, verify, press_enter, press_back

If goal achieved: {{"completed": true, "reasoning": "explanation"}}
If stuck/failed: {{"failed": true, "reasoning": "explanation"}}

CRITICAL: Return ONLY valid JSON, no markdown, no explanations."""

        try:
            # Build context about recent actions
            recent_actions_context = ""
            if actions_taken:
                recent_actions = actions_taken[-3:]  # Last 3 actions for context
                actions_summary = []
                for i, action in enumerate(recent_actions):
                    step_num = len(actions_taken) - len(recent_actions) + i + 1
                    actions_summary.append(
                        f"Step {step_num}: {action.action_type.value} on '{action.target_description}'"
                    )
                recent_actions_context = f"\n\nRecent actions taken:\n" + "\n".join(
                    actions_summary
                )

            user_content = f"Current goal: {goal_instruction}{recent_actions_context}"

            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle markdown code blocks and clean up)
            import re

            # Remove markdown code blocks if present
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object in the content
                json_match = re.search(
                    r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", content, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # If no JSON found, try the whole content
                    json_str = content

            # Clean up the JSON string
            json_str = json_str.strip()

            # Parse JSON response
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                console.print(f"✗ Invalid JSON from AI: {json_str[:100]}...")
                console.print(f"✗ JSON Error: {str(e)}")
                return None

            # Check if test is completed or failed
            if result.get("completed"):
                console.print(
                    f"✓ Goal achieved: {result.get('reasoning', 'Task completed')}"
                )
                return None

            if result.get("failed"):
                console.print(
                    f"✗ Test failed: {result.get('reasoning', 'Unable to proceed')}"
                )
                return None

            # Validate result structure
            if not isinstance(result, dict):
                console.print(f"✗ AI response is not a JSON object: {type(result)}")
                return None

            if "action_type" not in result or "target_description" not in result:
                console.print(f"✗ AI response missing required fields: {result}")
                return None

            try:
                # Create TestAction from response
                action = TestAction(
                    action_type=ActionType(result["action_type"]),
                    target_description=result["target_description"],
                    parameters=result.get("parameters", {}),
                    reasoning=result.get("reasoning", "AI decision"),
                )

                console.print(f"AI Decision: {action.reasoning}")
                return action
            except ValueError as e:
                console.print(
                    f"✗ Invalid action_type '{result.get('action_type')}': {str(e)}"
                )
                return None

        except json.JSONDecodeError as e:
            console.print(f"✗ Failed to parse AI response: {str(e)}")
            return None
        except Exception as e:
            console.print(f"✗ Error getting next action: {str(e)}")
            return None

    def _format_elements_for_ai(self, elements: List[UIElement]) -> str:
        """Format UI elements for AI analysis"""
        if not elements:
            return "No interactive elements found on screen"

        formatted = []
        for i, element in enumerate(elements[:15]):  # Limit to first 15 elements
            desc = f"{i+1}. "
            if element.text:
                desc += f"Text: '{element.text}' "
            if element.resource_id:
                desc += f"ID: {element.resource_id} "
            if element.class_name:
                desc += f"Type: {element.class_name} "
            if element.content_desc:
                desc += f"Description: '{element.content_desc}' "
            desc += f"Bounds: {element.bounds}"
            formatted.append(desc)

        return "\n".join(formatted)

    async def parse_natural_language_test(
        self, test_instruction: str
    ) -> List[TestAction]:
        """DEPRECATED: Parse a natural language test instruction into structured actions

        This method is kept for backwards compatibility but the new dynamic approach
        using decide_next_action() is preferred.
        """

        system_prompt = """You are an expert mobile app testing assistant. Your job is to parse natural language test instructions into structured test actions.

Given a test instruction, break it down into a sequence of specific actions. Each action should specify:
1. The action type (click, long_click, set_text, clear_text, scroll, wait, verify, press_enter, press_back)
2. A clear description of the target element 
3. Any parameters needed (e.g., text to enter, scroll direction)

IMPORTANT: When entering text in search bars, input fields, or forms, automatically add a "press_enter" action after "set_text" to submit/search/confirm the input.

Return your response as a JSON array of actions. Each action should have:
- action_type: one of the ActionType enum values
- target_description: clear description of what element to interact with
- parameters: object with any additional parameters needed

Example:
Input: "Click on the login button, then enter 'john@example.com' in the email field and 'password123' in the password field, then click submit"

Output:
[
  {
    "action_type": "click",
    "target_description": "login button",
    "parameters": {}
  },
  {
    "action_type": "set_text", 
    "target_description": "email field",
    "parameters": {"text": "john@example.com"}
  },
  {
    "action_type": "set_text",
    "target_description": "password field", 
    "parameters": {"text": "password123"}
  },
  {
    "action_type": "click",
    "target_description": "submit button",
    "parameters": {}
  }
]

Be precise and break down complex instructions into simple, atomic actions."""

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Parse this test instruction: {test_instruction}",
                    },
                ],
                temperature=0,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from the response
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                actions_data = json.loads(json_match.group())
            else:
                # Try to parse the entire content as JSON
                actions_data = json.loads(content)

            # Convert to TestAction objects
            actions = []
            for action_data in actions_data:
                try:
                    action = TestAction(
                        action_type=ActionType(action_data["action_type"]),
                        target_description=action_data["target_description"],
                        parameters=action_data.get("parameters", {}),
                    )
                    actions.append(action)
                except (KeyError, ValueError) as e:
                    console.print(
                        f"Warning: Skipping invalid action: {action_data}, error: {e}"
                    )

            console.print(f"✓ Parsed {len(actions)} actions from test instruction")
            return actions

        except Exception as e:
            console.print(f"✗ Failed to parse test instruction: {str(e)}")
            raise

    async def select_best_element(
        self,
        target_description: str,
        available_elements: List[UIElement],
        current_screen_context: str = "",
    ) -> SelectorDecision:
        """Use AI to select the best UI element based on the target description"""

        # Prepare element information for the AI
        elements_info = []
        for i, element in enumerate(available_elements):
            selectors = element.get_selector_options()
            element_desc = {
                "index": i,
                "text": element.text,
                "content_desc": element.content_desc,
                "resource_id": element.resource_id,
                "class_name": element.class_name,
                "clickable": element.clickable,
                "enabled": element.enabled,
                "scrollable": element.scrollable,
                "checkable": element.checkable,
                "available_selectors": selectors[:3],  # Top 3 selector options
            }
            elements_info.append(element_desc)

        system_prompt = """You are an expert mobile app testing assistant. Your job is to select the best UI element that matches a given target description.

Given:
1. A target description (what the user wants to interact with)
2. A list of available UI elements with their properties and selector options
3. Optional screen context

Select the most appropriate element and return:
1. The best selector code to use
2. Your reasoning for the choice
3. A confidence score (0.0 to 1.0)
4. Alternative selectors if applicable

Consider:
- Text matches (exact or partial)
- Content descriptions 
- Resource IDs that make semantic sense
- Element types (buttons, text fields, EditText, etc.)
- Whether the element is interactive (clickable/enabled)
- Similar or related functionality (e.g., "search" could match "omnibox", "url bar", etc.)
- Be flexible with descriptions - users might describe things differently

Return as JSON:
{
  "selected_selector": "d(text='Login')",
  "reasoning": "This button has the exact text 'Login' and is clickable",
  "confidence": 0.95,
  "alternative_selectors": ["d(resourceId='login_btn')", "d(className='android.widget.Button')"]
}

Be more lenient and try to find the best available match even if not perfect. Only return confidence < 0.3 if absolutely no reasonable match exists."""

        user_prompt = f"""Target: {target_description}

Screen Context: {current_screen_context}

Available Elements:
{json.dumps(elements_info, indent=2)}

Select the best element and selector for the target: "{target_description}"
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=1000,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from the response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group())
            else:
                decision_data = json.loads(content)

            decision = SelectorDecision(
                selected_selector=decision_data["selected_selector"],
                reasoning=decision_data["reasoning"],
                confidence=float(decision_data["confidence"]),
                alternative_selectors=decision_data.get("alternative_selectors", []),
            )

            console.print(
                f"✓ Selected element with confidence {decision.confidence:.2f}"
            )
            console.print(f"Reasoning: {decision.reasoning}")

            return decision

        except Exception as e:
            console.print(f"✗ Failed to select element: {str(e)}")
            raise

    async def analyze_test_result(
        self, action: TestAction, success: bool, error_message: str = ""
    ) -> Dict[str, Any]:
        """Analyze the result of a test action and provide feedback"""

        system_prompt = """You are an expert mobile app testing assistant. Analyze the result of a test action and provide feedback.

Given:
1. The test action that was attempted
2. Whether it succeeded or failed
3. Any error message if it failed

Provide:
1. Analysis of what happened
2. Suggestions for improvement if it failed
3. Next steps or things to watch for

Return as JSON:
{
  "analysis": "Description of what happened",
  "suggestions": ["List of suggestions if failed"],
  "severity": "low|medium|high",
  "should_continue": true/false
}"""

        action_info = {
            "action_type": action.action_type.value,
            "target_description": action.target_description,
            "parameters": action.parameters,
            "selector_used": action.selector_code,
            "success": success,
            "error_message": error_message,
        }

        user_prompt = f"""Analyze this test action result:

Action: {json.dumps(action_info, indent=2)}

Provide analysis and suggestions."""

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=800,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from the response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = json.loads(content)

            return analysis

        except Exception as e:
            console.print(f"✗ Failed to analyze test result: {str(e)}")
            return {
                "analysis": f"Failed to analyze: {str(e)}",
                "suggestions": [],
                "severity": "medium",
                "should_continue": True,
            }

    async def generate_test_report(
        self, test_name: str, actions: List[TestAction], results: List[Dict[str, Any]]
    ) -> str:
        """Generate a comprehensive test report"""

        system_prompt = """Generate a comprehensive test report in markdown format.

Include:
1. Test summary
2. Actions performed
3. Results for each action
4. Overall pass/fail status
5. Recommendations

Make it clear and professional."""

        test_data = {
            "test_name": test_name,
            "total_actions": len(actions),
            "actions_and_results": [],
        }

        for action, result in zip(actions, results):
            test_data["actions_and_results"].append(
                {
                    "action": {
                        "type": action.action_type.value,
                        "target": action.target_description,
                        "parameters": action.parameters,
                    },
                    "result": result,
                }
            )

        user_prompt = f"""Generate a test report for:

{json.dumps(test_data, indent=2)}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=1500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            console.print(f"✗ Failed to generate test report: {str(e)}")
            return f"# Test Report\n\nFailed to generate report: {str(e)}"


if __name__ == "__main__":
    # Test the Azure agent
    async def test_agent():
        agent = AzureAgent()

        # Test parsing
        test_instruction = (
            "Click on the login button and enter 'test@example.com' in the email field"
        )
        actions = await agent.parse_natural_language_test(test_instruction)

        print(f"Parsed {len(actions)} actions:")
        for action in actions:
            print(f"- {action.action_type.value}: {action.target_description}")

    # Uncomment to test (requires Azure OpenAI credentials)
    # asyncio.run(test_agent())
