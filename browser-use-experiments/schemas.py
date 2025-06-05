from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Selector(BaseModel):
    """Represents a single selector with its type and value."""

    type: str = Field(..., description="Type of selector (css, xpath, index, etc.)")
    value: str | int = Field(..., description="The actual selector value or index")


class SelectorGroup(BaseModel):
    """Group of selectors with a primary and optional fallbacks."""

    primary: Selector = Field(..., description="Primary selector to try first")
    fallback: Optional[List[Selector]] = Field(
        default=None, description="List of fallback selectors to try if primary fails"
    )


class ActionParams(BaseModel):
    """Parameters for specific actions (e.g., text for input, URL for navigation)."""

    text: Optional[str] = Field(default=None, description="Text to input or search for")
    url: Optional[str] = Field(default=None, description="URL to navigate to")
    wait_time: Optional[float] = Field(
        default=None, description="Time to wait in seconds"
    )
    button_type: Optional[str] = Field(
        default=None, description="Type of button if applicable"
    )
    # Add more parameters as needed


class ElementAttributes(BaseModel):
    """Attributes of the DOM element being interacted with."""

    tag_name: Optional[str] = Field(default=None, description="HTML tag name")
    attributes: Optional[Dict[str, Any]] = Field(
        default=None, description="Dictionary of element attributes"
    )
    xpath: Optional[str] = Field(default=None, description="Full XPath of the element")
    css_selector: Optional[str] = Field(
        default=None, description="Full CSS selector of the element"
    )


class Assertion(BaseModel):
    """Assertion to verify before or after an action."""

    type: str = Field(
        ..., description="Type of assertion (visible, present, text_equals, etc.)"
    )
    selector: str = Field(..., description="Selector to check")
    expected_value: Optional[str] = Field(
        default=None, description="Expected value for the assertion"
    )
    timeout: Optional[float] = Field(
        default=None, description="Timeout in seconds for the assertion"
    )


class BrowserAction(BaseModel):
    """Complete schema for a single browser action step."""

    step_index: int = Field(..., description="Order of the action in the sequence")
    action_type: str = Field(
        ..., description="Type of action (click, fill, goto, etc.)"
    )
    selectors: SelectorGroup = Field(
        ..., description="Group of selectors for the action"
    )
    action_params: Optional[ActionParams] = Field(
        default=None, description="Parameters specific to the action type"
    )
    element_attributes: Optional[ElementAttributes] = Field(
        default=None, description="Attributes of the element being interacted with"
    )
    context: Optional[str] = Field(
        default=None, description="Context or reasoning for this action"
    )
    assertion: Optional[Assertion] = Field(
        default=None, description="Assertion to verify before or after the action"
    )


class BrowserActionSequence(BaseModel):
    """Sequence of browser actions."""

    actions: List[BrowserAction] = Field(
        ..., description="List of browser actions in sequence"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the sequence"
    )
