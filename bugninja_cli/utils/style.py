from enum import Enum
from typing import Tuple

import rich_click as click


class Palette(Tuple[int, int, int], Enum):
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
    click.secho(ASCII_ART, fg=Palette.MAIN, bold=True)
    click.secho(
        "Fully automated AI-based testing that never sleeps! ",
        fg=Palette.ACCENT,
        bold=True,
        nl=False,
    )
    click.echo("🤖")
    # TODO! use dynamic version display here
    pride_version_num: str = "0.1.0"
    click.secho(f"Version {pride_version_num}", italic=True)
