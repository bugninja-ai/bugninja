from typing import Dict, List, Optional
from lxml import html
from rich import print as rich_print
from lxml.etree import _Element as Element
from lxml.html import HtmlElement
from enum import Enum


class SelectorSpecificity(str, Enum):
    NOT_FOUND = 1
    MULTIPLE_MATCH = 2
    UNIQUE_MATCH = 3


class SelectorFactory:
    def __init__(self, html_content: str):
        self.tree: HtmlElement = html.fromstring(html_content)

    @staticmethod
    def log_element(element: Element):
        rich_print("-----")
        rich_print("ID:")
        rich_print("Tag:")
        rich_print(element.tag)
        rich_print("Attributes:")
        rich_print({k: v for k, v in element.attrib.items()})
        rich_print("Text:")
        rich_print(element.text)

    def evaluate_selector_on_page(self, xpath: str) -> SelectorSpecificity:
        found_elements = self.tree.xpath(xpath)
        if len(found_elements) == 0:
            return SelectorSpecificity.NOT_FOUND
        elif len(found_elements) > 1:
            return SelectorSpecificity.MULTIPLE_MATCH
        else:
            return SelectorSpecificity.UNIQUE_MATCH

    @staticmethod
    def generate_xpaths_for_element(e: Element) -> List[str]:
        xpath_list: List[str] = []

        if e.tag is not None:
            xpath_list.append(f"//{e.tag}")

            if e.text is not None:
                xpath_list.append(f"//{e.tag}[text()='{e.text.strip()}']")

            attributes_dict: Dict[str, str] = {key: value for key, value in e.attrib.items()}

            if "id" in attributes_dict:
                xpath_list.append(f"//{e.tag}[@id='{attributes_dict['id']}']")

            #! right now we only check for specific class names at once, no combinations/permutations
            if "class" in attributes_dict:
                class_name_list: List[str] = attributes_dict["class"].split(" ")
                for class_name in class_name_list:
                    xpath_list.append(f"//{e.tag}[contains(@class, '{class_name}')]")

        return xpath_list

    def get_valid_xpaths_of_element(self, e: Element) -> List[str]:
        unique_xpaths: List[str] = []
        for x_path in self.generate_xpaths_for_element(e=e):
            type_of_match: SelectorSpecificity = self.evaluate_selector_on_page(xpath=x_path)

            match type_of_match:
                case SelectorSpecificity.NOT_FOUND:
                    # rich_print(f"🔴 X-Path not found:")
                    print(x_path)
                    continue
                case SelectorSpecificity.MULTIPLE_MATCH:
                    # rich_print(f"🟡 X-Path not unique:")
                    print(x_path)
                    continue
                case SelectorSpecificity.UNIQUE_MATCH:
                    # rich_print(f"🟢 X-Path unique:")
                    print(x_path)
                    unique_xpaths.append(x_path)

        return unique_xpaths

    def generate_relative_xpath_from_full_xpath(self, full_xpath: str) -> str:

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
