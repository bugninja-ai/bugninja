"""
Styling utilities for Bugninja CLI.

This module provides **styling and formatting utilities** for the Bugninja CLI,
including color palettes, ASCII art, and markdown configuration for rich
command-line interfaces.

## Key Components

1. **Palette** - Color palette enumeration for consistent styling
2. **MARKDOWN_CONFIG** - Rich Click markdown configuration
3. **ASCII_ART** - Bugninja logo in ASCII format
4. **display_logo()** - Function to display the Bugninja logo

## Usage Examples

```python
from bugninja_cli.utils.style import display_logo, MARKDOWN_CONFIG

# Display the Bugninja logo
display_logo()

# Use markdown configuration in Click commands
@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
def my_command():
    pass
```
"""

import tomllib
from enum import Enum
from typing import Any, Tuple
from importlib.metadata import version as get_package_version, PackageNotFoundError

import rich_click as click


class Palette(Tuple[int, int, int], Enum):
    """Color palette for Bugninja CLI styling.

    This enumeration defines the color scheme used throughout the Bugninja CLI
    for consistent visual styling and branding.

    Attributes:
        MAIN (Tuple[int, int, int]): Primary brand color (78, 59, 199)
        ACCENT (Tuple[int, int, int]): Accent color for highlights (255, 255, 255)
        DARK (Tuple[int, int, int]): Dark color for backgrounds (33, 28, 75)
    """

    MAIN = 78, 59, 199
    ACCENT = 255, 255, 255
    DARK = 33, 28, 75


MARKDOWN_CONFIG = click.RichHelpConfiguration(text_markup="markdown")

ASCII_ART = r"""
______                   _       _       
| ___ \                 (_)     (_)      
| |_/ /_   _  __ _ _ __  _ _ __  _  __ _ 
| ___ \ | | |/ _` | '_ \| | '_ \| |/ _` |
| |_/ / |_| | (_| | | | | | | | | | (_| |
\____/ \__,_|\__, |_| |_|_|_| |_| |\__,_|
              __/ |            _/ |      
             |___/            |__/       
"""


def display_logo() -> None:
    """Display the Bugninja logo with version information.

    This function displays the Bugninja ASCII art logo with the main brand color,
    followed by the tagline and version information. It provides a consistent
    branding experience across the CLI.

    Notes:
        - Uses the main brand color for the ASCII art
        - Displays the tagline in accent color
        - Shows current version in italic style
        - Includes emoji for visual appeal
    """
    click.secho(ASCII_ART, fg=Palette.MAIN, bold=True)
    click.secho(
        "Fully automated AI-based testing that never sleeps! ",
        fg=Palette.ACCENT,
        bold=True,
        nl=False,
    )
    click.echo("🤖")

    def get_version() -> str:
        try:
            return get_package_version("bugninja")
        except PackageNotFoundError:
            # Fallback to reading pyproject.toml if package is not installed
            try:
                with open("pyproject.toml", "rb") as f:
                    data: dict[str, Any] = tomllib.load(f)
                    return str(data["project"]["version"])
            except (FileNotFoundError, KeyError):
                return "version_not_found"

    version = get_version()
    click.secho(f"Version {version}", italic=True)
