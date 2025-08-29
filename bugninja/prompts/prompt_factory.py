import importlib.resources
from pathlib import Path
from typing import Dict, List


def __get_raw_prompt(prompt_markdown_name: str) -> str:
    try:
        # First, try to load using importlib.resources (for installed packages)
        with (
            importlib.resources.files("bugninja.prompts")
            .joinpath(prompt_markdown_name)
            .open("r", encoding="utf-8") as file
        ):
            return file.read()
    except (FileNotFoundError, ImportError):
        # Fallback to file system path (for development)
        current_file = Path(__file__)
        prompts_dir = current_file.parent.parent / "prompts"
        prompt_file = prompts_dir / prompt_markdown_name

        try:
            with open(prompt_file, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Markdown file not found: {prompt_file}")
        except IOError as e:
            raise IOError(f"Error reading markdown file {prompt_file}: {e}")


def __parsed_prompt(prompt_markdown_name: str, key_value_pairs: Dict[str, str]) -> str:
    raw_prompt: str = __get_raw_prompt(prompt_markdown_name)
    for k, v in key_value_pairs.items():
        raw_prompt = raw_prompt.replace(f"[[{k.upper()}]]", v)

    return raw_prompt


#! -------------------------


def get_extra_rules_related_prompt(extra_rule_list: List[str]) -> str:

    if not extra_rule_list:
        return ""

    return __parsed_prompt(
        "extra_rules_prompt.md", {"EXTRA_RULES": "\n-" + "\n-".join(extra_rule_list)}
    )


BUGNINJA_INITIAL_NAVIGATROR_SYSTEM_PROMPT: str = __get_raw_prompt(
    prompt_markdown_name="navigator_agent_system_prompt.md"
)
