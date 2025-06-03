"""
AI Client Module for BugNinja V2

This module handles:
1. Communication with Azure OpenAI
2. Analyzing available interactive elements
3. Making decisions about next actions
4. Providing reasoning for decisions
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from openai import AzureOpenAI
import asyncio
from dotenv import load_dotenv
import logging

# Load environment variables from .env file in the same directory
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)


@dataclass
class AIDecision:
    """AI decision about what action to take next"""

    action_type: str  # click, type, hover, scroll, select, wait, complete
    element_id: Optional[str]  # Which element to interact with
    text_input: Optional[str]  # Text to type (for type actions)
    option_value: Optional[str]  # Option to select (for select actions)
    reasoning: str  # AI's explanation of why this action was chosen
    confidence: float  # Confidence level (0.0 to 1.0)
    is_goal_complete: bool  # Whether the AI thinks the goal is achieved
    recommended_next_step: Optional[str] = (
        None  # What should be done next after this action
    )


@dataclass
class NavigationContext:
    """Context about the current navigation state"""

    current_url: str
    page_title: str
    goal: str
    previous_actions: List[Dict[str, Any]]
    step_number: int


class AIClient:
    """Handles AI decision making using Azure OpenAI"""

    def __init__(self, debug: bool = False):
        self.client = None
        self.model_name = None
        self.debug = debug
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Azure OpenAI client"""
        try:
            # Get configuration from environment variables
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            self.model_name = os.getenv("AZURE_MODEL_NAME", "gpt-4o")

            if not endpoint or not api_key:
                raise ValueError(
                    "Missing Azure OpenAI configuration. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables."
                )

            self.client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version="2024-02-15-preview",
            )

        except Exception as e:
            raise ValueError(f"Failed to initialize Azure OpenAI client: {str(e)}")

    async def decide_next_action(
        self,
        elements_summary: List[Dict[str, Any]],
        context: NavigationContext,
        page_screenshot: Optional[str] = None,
    ) -> AIDecision:
        """
        Analyze available elements and context to decide the next action

        Args:
            elements_summary: List of available interactive elements
            context: Current navigation context and goal
            page_screenshot: Optional base64 encoded screenshot

        Returns:
            AIDecision with the recommended action and goal achievement status
        """

        # Build the system prompt
        system_prompt = self._build_system_prompt()

        # Build the user prompt with current state
        user_prompt = self._build_user_prompt(
            elements_summary, context, page_screenshot
        )

        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Add screenshot if available
        if page_screenshot:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Current page screenshot for visual context:",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_screenshot}"
                            },
                        },
                    ],
                }
            )

        try:
            # Make the API call
            response = await self._make_api_call(messages)

            # Parse the response
            decision = self._parse_ai_response(response, elements_summary)

            return decision

        except Exception as e:
            # Return a fallback decision if AI call fails
            return AIDecision(
                action_type="wait",
                element_id=None,
                text_input=None,
                option_value=None,
                reasoning=f"AI decision failed: {str(e)}. Waiting for manual intervention.",
                confidence=0.0,
                is_goal_complete=False,
            )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI"""
        return """You are a web interface analysis assistant that provides recommendations for quality assurance testing.

Your role is to analyze web interface screenshots and provide structured recommendations about which interface elements a QA tester should interact with next.

Respond with this JSON structure:
{
    "goal_achieved": true/false,
    "action_type": "click|type|hover|scroll|select|wait|complete",
    "element_id": "elem_X or null",
    "text_input": "text or null",
    "option_value": "option or null", 
    "reasoning": "brief explanation",
    "confidence": 0.95,
    "recommended_next_step": "suggestion for next testing step"
}

CRITICAL ELEMENT SELECTION RULES:
- When you need to INPUT TEXT or WRITE CONTENT: ALWAYS choose textarea, input, or contenteditable elements - NEVER buttons
- For type actions: ONLY use elements with type "textarea", "input", or "contenteditable" 
- NEVER use buttons for typing text - buttons are for clicking only
- If the goal requires writing/typing text and you see textarea/input elements, you MUST choose them
- Buttons with labels like "Type here" or "Enter text" are NOT for typing - find the actual text input field

IMPORTANT RULES:
- For actions click, type, hover, scroll, select: ALWAYS provide a valid element_id from the elements list
- For type actions: Use textarea, input, or contenteditable elements ONLY
- For scroll actions: Specify which element to scroll to (don't leave element_id as null)
- Only use element IDs that exist in the provided elements list
- If you see a text area or input field that needs content, choose "type" action with that element's ID
- The website you are testing can be in any language but you should keep everything in English in the responses 

Analysis guidelines:
- Examine the provided screenshot to understand the current interface state
- Identify which interactive element from the element list would be most relevant for testing
- Recommend the appropriate testing interaction for that element
- Prioritize interface elements that might block other interactions (like modals or popups)
- For text input requirements, ALWAYS look for textarea, input, or contenteditable elements - ignore buttons

Available interaction types: click, type, hover, scroll, select, wait, complete"""

    def _build_user_prompt(
        self,
        elements_summary: List[Dict[str, Any]],
        context: NavigationContext,
        page_screenshot: Optional[str] = None,
    ) -> str:
        """Build the user prompt with current state information"""

        # Simple element listing with position info for modal detection
        elements_text = "Available Elements:\n"

        # Sort elements to prioritize text inputs when goal involves typing
        def element_priority(element):
            # Higher priority (lower number) for text inputs if goal involves typing
            if any(
                keyword in context.goal.lower()
                for keyword in ["type", "write", "input", "text", "enter"]
            ):
                if element["type"] in ["textarea", "input", "contenteditable"]:
                    return 0  # Highest priority
                elif element["type"] == "button":
                    return 2  # Lower priority
                else:
                    return 1
            return 1

        sorted_elements = sorted(elements_summary[:15], key=element_priority)

        for element in sorted_elements:
            position = element["position"]

            # Add special markers for text input elements
            type_marker = ""
            if element["type"] in ["textarea", "input", "contenteditable"]:
                type_marker = "🔥 TEXT INPUT 🔥 "

            element_info = f"- {element['id']}: {type_marker}{element['type']} '{element['text'][:50]}'"

            # Add key attributes
            if element["placeholder"]:
                element_info += f" (placeholder: '{element['placeholder']}')"
            if "type" in element["attributes"]:
                element_info += f" [type: {element['attributes']['type']}]"

            # Add position for modal detection
            element_info += f" at (x:{position['x']:.0f}, y:{position['y']:.0f})"

            elements_text += element_info + "\n"

        # Simple action history
        action_history = ""
        if context.previous_actions:
            action_history = "\nRecent Actions:\n"
            for action in context.previous_actions[-2:]:  # Last 2 actions only
                status = "SUCCESS" if action.get("result") else "FAILED"
                action_history += (
                    f"- {action['action']} on {action['element_id']}: {status}\n"
                )

        prompt = f"""Interface Analysis Request

Testing Scenario: {context.goal}
Current Page: {context.current_url}
{action_history}

Available Interface Elements:
{elements_text}

Please analyze the provided screenshot and interface elements to recommend the next testing interaction.

Analysis Requirements:
- Use the screenshot to understand the current interface state
- Identify any blocking elements (modals, popups) that should be addressed first
- Select an element ID from the list above (do not create new IDs)
- Recommend the most appropriate testing interaction

What element and interaction would you recommend for the next testing step?"""

        return prompt

    async def _make_api_call(self, messages: List[Dict]) -> str:
        """Make the actual API call to Azure OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.05,  # Very low temperature for consistent decisions
                response_format={"type": "json_object"},  # Ensure JSON response
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Azure OpenAI API call failed: {str(e)}")

    def _parse_ai_response(
        self, response: str, elements_summary: List[Dict[str, Any]]
    ) -> AIDecision:
        """Parse the AI response and validate it"""
        try:
            # Debug: Print the raw AI response only in debug mode
            if self.debug:
                print(f"\n🤖 AI RAW RESPONSE:")
                print(response)
                print("=" * 50)

            # Parse JSON response
            data = json.loads(response)

            # Validate required fields
            required_fields = [
                "goal_achieved",
                "action_type",
                "reasoning",
                "confidence",
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Validate action type
            valid_actions = [
                "click",
                "type",
                "hover",
                "scroll",
                "select",
                "wait",
                "complete",
            ]
            if data["action_type"] not in valid_actions:
                raise ValueError(f"Invalid action type: {data['action_type']}")

            # Actions that require an element ID
            actions_requiring_element = ["click", "type", "hover", "scroll", "select"]

            # Validate element_id if provided
            element_id = data.get("element_id")
            if element_id and element_id != "null":
                element_exists = any(
                    elem["id"] == element_id for elem in elements_summary
                )
                if not element_exists:
                    # Provide helpful error with available element IDs
                    available_ids = [elem["id"] for elem in elements_summary[:10]]
                    raise ValueError(
                        f"Element ID '{element_id}' not found. Available element IDs: {', '.join(available_ids)}"
                    )

            # Check if action requires element but none provided
            if data["action_type"] in actions_requiring_element:
                if not element_id or element_id == "null" or element_id == "None":
                    # Try to find a reasonable default element for this action type
                    if data["action_type"] == "type":
                        # Find first input or textarea
                        for elem in elements_summary:
                            if elem["type"] in ["input", "textarea", "contenteditable"]:
                                element_id = elem["id"]
                                if self.debug:
                                    print(
                                        f"⚠️ AI didn't provide element ID for type action, using first text input: {element_id}"
                                    )
                                break
                    elif data["action_type"] == "scroll":
                        # For scroll, we can often scroll the page without specific element
                        # But if AI meant to scroll to something, try to find a reasonable target
                        if elements_summary:
                            # Use the first visible element as scroll target
                            element_id = elements_summary[0]["id"]
                            if self.debug:
                                print(
                                    f"⚠️ AI didn't provide element ID for scroll action, using first element: {element_id}"
                                )
                    else:
                        # For click, hover, select - we need a specific element
                        available_ids = [elem["id"] for elem in elements_summary[:5]]
                        raise ValueError(
                            f"Action '{data['action_type']}' requires an element ID but none provided. Available: {', '.join(available_ids)}"
                        )

            # CRITICAL VALIDATION: Prevent AI from choosing buttons for typing
            if data["action_type"] == "type" and element_id:
                selected_element = None
                for elem in elements_summary:
                    if elem["id"] == element_id:
                        selected_element = elem
                        break

                if selected_element and selected_element["type"] not in [
                    "textarea",
                    "input",
                    "contenteditable",
                ]:
                    if self.debug:
                        print(
                            f"🚨 AI incorrectly chose {selected_element['type']} {element_id} for typing! Finding proper text input..."
                        )

                    # Find a proper text input element
                    text_input_found = None
                    for elem in elements_summary:
                        if elem["type"] in ["textarea", "input", "contenteditable"]:
                            text_input_found = elem["id"]
                            if self.debug:
                                print(
                                    f"✅ Corrected to use text input: {text_input_found} (type: {elem['type']})"
                                )
                            break

                    if text_input_found:
                        element_id = text_input_found
                        # Update the reasoning to reflect the correction
                        data["reasoning"] = (
                            f"🚨 CORRECTED: AI chose {selected_element['type']} for typing, auto-corrected to proper text input {text_input_found}. {data['reasoning']}"
                        )
                    else:
                        raise ValueError(
                            f"AI chose {selected_element['type']} for typing but no text input elements available!"
                        )

            # Validate confidence
            confidence = float(data["confidence"])
            if not 0.0 <= confidence <= 1.0:
                confidence = max(0.0, min(1.0, confidence))  # Clamp to valid range

            # Extract goal achievement status
            goal_achieved = bool(data.get("goal_achieved", False))

            # If goal is achieved, force action type to complete
            if goal_achieved and data["action_type"] != "complete":
                data["action_type"] = "complete"

            # Create AIDecision object
            return AIDecision(
                action_type=data["action_type"],
                element_id=(
                    element_id
                    if element_id != "null" and element_id != "None"
                    else None
                ),
                text_input=(
                    data.get("text_input") if data.get("text_input") != "null" else None
                ),
                option_value=(
                    data.get("option_value")
                    if data.get("option_value") != "null"
                    else None
                ),
                reasoning=data["reasoning"],
                confidence=confidence,
                is_goal_complete=goal_achieved,
                recommended_next_step=data.get("recommended_next_step"),
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from AI: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse AI response: {str(e)}")

    async def validate_goal_completion(
        self,
        goal: str,
        current_url: str,
        page_title: str,
        elements_summary: List[Dict[str, Any]],
        page_screenshot: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validate if the goal has been completed

        Returns:
            (is_complete, explanation)
        """

        system_prompt = """You are an expert at determining if web navigation goals have been achieved. 
                    
            You will analyze the current page state and determine if the given goal has been completed.

            Respond with a JSON object:
            {
                "is_complete": true/false,
                "explanation": "clear explanation of why the goal is or isn't complete"
            }

            Be conservative - only mark as complete if you're confident the goal has been fully achieved."""

        user_prompt = f"""Goal: {goal}

            Current State:
            URL: {current_url}
            Page Title: {page_title}

            Available Elements: {len(elements_summary)} interactive elements found

            Has this goal been completed based on the current page state?"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if page_screenshot:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Current page screenshot:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_screenshot}"
                            },
                        },
                    ],
                }
            )

        try:
            response = await self._make_api_call(messages)
            data = json.loads(response)

            return bool(data.get("is_complete", False)), data.get(
                "explanation", "No explanation provided"
            )

        except Exception as e:
            return False, f"Could not validate goal completion: {str(e)}"

    def get_client_info(self) -> Dict[str, str]:
        """Get information about the AI client configuration"""
        return {
            "model": self.model_name,
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "Not configured"),
            "status": "Connected" if self.client else "Not connected",
        }
