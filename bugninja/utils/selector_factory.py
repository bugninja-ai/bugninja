from enum import Enum
from typing import Any, Dict, List, Optional

from lxml import html
from lxml.etree import _Element as Element
from lxml.html import HtmlElement
from rich import print as rich_print


class SelectorSpecificity(str, Enum):
    NOT_FOUND = 1
    MULTIPLE_MATCH = 2
    UNIQUE_MATCH = 3


BANNED_XPATH_TAG_ELEMENTS: List[str] = ["script"]


class SelectorFactory:
    def __init__(self, html_content: str):
        self.tree: HtmlElement = html.fromstring(html_content)

    def evaluate_selector_on_page(self, xpath: str) -> SelectorSpecificity:

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
        unique_xpaths: List[str] = []
        for x_path in self.generate_xpaths_for_element(e=e):
            type_of_match: SelectorSpecificity = self.evaluate_selector_on_page(xpath=x_path)

            if type_of_match == SelectorSpecificity.UNIQUE_MATCH:
                unique_xpaths.append(x_path)

        return unique_xpaths

    def generate_relative_xpaths_from_full_xpath(self, full_xpath: str) -> List[str]:

        nodes: List[Element] = self.tree.xpath(full_xpath)

        if len(nodes) == 0:
            raise ValueError("No element found for the provided XPath.")
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

        # except Exception as e:
        #     rich_print(e)

        rich_print("COLLECTED XPATHS:")
        rich_print(all_collected_xpath)
        return all_collected_xpath
