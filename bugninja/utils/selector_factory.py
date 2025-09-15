"""
XPath selector generation and validation utilities for Bugninja framework.

This module provides utilities for generating, validating, and working with
XPath selectors for web elements. It includes functionality for creating
relative XPath selectors, evaluating selector specificity, and generating
multiple selector variations for robust element targeting.

## Key Components

1. **SelectorSpecificity** - Enum for selector match results
2. **SelectorFactory** - Main class for XPath generation and validation
3. **BANNED_XPATH_TAG_ELEMENTS** - List of HTML tags to exclude from selectors

## Usage Examples

```python
from bugninja.utils import SelectorFactory

# Create factory with HTML content
factory = SelectorFactory(html_content)

# Generate selectors for an element
selectors = factory.generate_relative_xpaths_from_full_xpath("/html/body/button")

# Evaluate selector specificity
specificity = factory.evaluate_selector_on_page("//button[@id='submit']")
```
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from lxml import html
from lxml.etree import _Element as Element
from lxml.html import HtmlElement
from rich import print as rich_print


class SelectorSpecificity(str, Enum):
    """Enumeration of XPath selector match results.

    This enum represents the different outcomes when evaluating an XPath
    selector against HTML content.

    Values:
        NOT_FOUND (1): No elements found matching the selector
        MULTIPLE_MATCH (2): Multiple elements found matching the selector
        UNIQUE_MATCH (3): Exactly one element found matching the selector

    Example:
        ```python
        specificity = factory.evaluate_selector_on_page("//button")
        if specificity == SelectorSpecificity.UNIQUE_MATCH:
            print("Selector is unique and valid")
        ```
    """

    NOT_FOUND = 1
    MULTIPLE_MATCH = 2
    UNIQUE_MATCH = 3


BANNED_XPATH_TAG_ELEMENTS: List[str] = ["script"]


class SelectorFactory:
    """Factory for generating and validating XPath selectors.

    This class provides comprehensive XPath selector generation and validation
    functionality, including the ability to create relative selectors, evaluate
    selector specificity, and generate multiple selector variations for robust
    element targeting.

    Attributes:
        tree (HtmlElement): Parsed HTML tree from the provided content

    Example:
        ```python
        from bugninja.utils import SelectorFactory

        # Create factory with HTML content
        factory = SelectorFactory(html_content)

        # Generate selectors for an element
        selectors = factory.generate_relative_xpaths_from_full_xpath("/html/body/button")

        # Evaluate selector specificity
        specificity = factory.evaluate_selector_on_page("//button[@id='submit']")
        ```
    """

    def __init__(self, html_content: str):
        """Initialize the SelectorFactory with HTML content.

        Args:
            html_content (str): HTML content to parse and work with
        """
        self.tree: HtmlElement = html.fromstring(html_content)

    def evaluate_selector_on_page(self, xpath: str) -> SelectorSpecificity:
        """Evaluate XPath selector and return its specificity.

        Args:
            xpath (str): XPath selector to evaluate

        Returns:
            SelectorSpecificity: Result of the selector evaluation

        Example:
            ```python
            specificity = factory.evaluate_selector_on_page("//button[@id='submit']")
            if specificity == SelectorSpecificity.UNIQUE_MATCH:
                print("Selector is unique and valid")
            ```
        """

        found_elements: Optional[Any] = None

        try:
            found_elements = self.tree.xpath(xpath)
        except Exception as e:
            rich_print(f"Invalid XPath expression: {xpath}\nError: {e}\n-----")
            rich_print(e)

        if not found_elements:
            return SelectorSpecificity.NOT_FOUND

        if len(found_elements) == 0:
            return SelectorSpecificity.NOT_FOUND
        elif len(found_elements) > 1:
            return SelectorSpecificity.MULTIPLE_MATCH
        else:
            return SelectorSpecificity.UNIQUE_MATCH

    @staticmethod
    def generate_xpaths_for_element(e: Element) -> List[str]:
        """Generate multiple XPath selectors for a given element.

        Args:
            e (Element): XML/HTML element to generate selectors for

        Returns:
            List[str]: List of XPath selectors for the element

        Example:
            ```python
            selectors = SelectorFactory.generate_xpaths_for_element(element)
            # Returns: ["//button", "//button[@id='submit']", "//button[contains(@class, 'btn')]"]
            ```
        """
        xpath_list: List[str] = []
        attributes_dict: Dict[str, str] = {key: value for key, value in e.attrib.items()}

        if e.tag is None or not isinstance(e.tag, str) or e.tag in BANNED_XPATH_TAG_ELEMENTS:
            return xpath_list

        xpath_list.append(f"//{e.tag}")  # type: ignore

        if e.text is not None:
            xpath_list.append(f"//{e.tag}[text()='{e.text.strip()}']")  # type: ignore

        if "id" in attributes_dict:
            xpath_list.append(f"//{e.tag}[@id='{attributes_dict['id']}']")  # type: ignore

        #! right now we only check for specific class names at once, no combinations/permutations
        if "class" in attributes_dict:
            class_name_list: List[str] = [
                class_name for class_name in attributes_dict["class"].split(" ") if class_name != ""
            ]
            for class_name in class_name_list:
                xpath_list.append(f"//{e.tag}[contains(@class, '{class_name}')]")  # type: ignore

        return xpath_list

    def get_valid_xpaths_of_element(self, e: Element) -> List[str]:
        """Get valid (unique) XPath selectors for an element.

        Args:
            e (Element): XML/HTML element to get valid selectors for

        Returns:
            List[str]: List of XPath selectors that uniquely identify the element

        Example:
            ```python
            valid_selectors = factory.get_valid_xpaths_of_element(element)
            # Returns only selectors that match exactly one element
            ```
        """
        unique_xpaths: List[str] = []
        for x_path in self.generate_xpaths_for_element(e=e):
            type_of_match: SelectorSpecificity = self.evaluate_selector_on_page(xpath=x_path)

            if type_of_match == SelectorSpecificity.UNIQUE_MATCH:
                unique_xpaths.append(x_path)

        return unique_xpaths

    def generate_relative_xpaths_from_full_xpath(self, full_xpath: str) -> List[str]:
        """Generate relative XPath selectors from a full XPath.

        Args:
            full_xpath (str): Full XPath selector to generate relative selectors from

        Returns:
            List[str]: List of relative XPath selectors

        Raises:
            ValueError: If no element is found or multiple elements are found for the XPath

        Example:
            ```python
            relative_selectors = factory.generate_relative_xpaths_from_full_xpath("/html/body/button")
            # Returns: ["//button", "//button[@id='submit']", etc.]
            ```
        """

        nodes: List[Element] = self.tree.xpath(full_xpath)

        if len(nodes) == 0:
            raise ValueError(f"No element found for the provided XPath: `{full_xpath}`")
        elif len(nodes) > 1:
            raise ValueError("Multiple elements found for the provided XPath.")

        root_node: Element = nodes[0]
        cur = root_node

        all_collected_xpath: List[str] = self.get_valid_xpaths_of_element(e=root_node)
        xpath_parts: List[str] = full_xpath.strip("/").split("/")[::-1]
        path_subparts: List[str] = []

        # ? for good measure we have to check for the child elements of the selectable element as well, but only for 1 level depth
        for child in cur:

            children_xpath_selectors: List[str] = []
            if (
                cur.tag is None
                or not isinstance(cur.tag, str)
                or cur.tag in BANNED_XPATH_TAG_ELEMENTS
            ):
                continue

            for child_xpath in self.get_valid_xpaths_of_element(e=child):
                children_xpath_selectors.append(
                    child_xpath + f"/parent::{cur.tag}"  # type:ignore
                )

            all_collected_xpath.extend(children_xpath_selectors)

        #! we iterate over the path from the last element to the root
        for last_element_identifier in xpath_parts:
            path_subparts.append(last_element_identifier)

            parent_of_current_element: Optional[Element] = cur.getparent()

            if parent_of_current_element is None:
                break

            cur = parent_of_current_element
            xpath_subsection: str = "/".join(path_subparts[::-1])

            all_collected_xpath.extend(
                [f"{x}/{xpath_subsection}" for x in self.get_valid_xpaths_of_element(e=cur)]
            )

            if len(all_collected_xpath) > 100:
                break

        return all_collected_xpath
