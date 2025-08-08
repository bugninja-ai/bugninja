#!/usr/bin/env python3
"""
Debug script to test Click colors and styling.
"""

import os

import click

# Force color output
os.environ["CLICK_COLORS"] = "1"
os.environ["FORCE_COLOR"] = "1"


def test_click_colors():
    """Test Click color support."""
    print("Testing Click colors...")
    print()

    # Test basic colors
    colors = ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]
    bright_colors = [
        "bright_red",
        "bright_green",
        "bright_blue",
        "bright_yellow",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
    ]

    print("=== Basic Colors ===")
    for color in colors:
        try:
            styled = click.style(f"This is {color}", fg=color, bold=True)
            print(styled)
        except Exception as e:
            print(f"Error with {color}: {e}")

    print()
    print("=== Bright Colors ===")
    for color in bright_colors:
        try:
            styled = click.style(f"This is {color}", fg=color, bold=True)
            print(styled)
        except Exception as e:
            print(f"Error with {color}: {e}")

    print()
    print("=== Test with our colors ===")
    try:
        styled = click.style("This is our primary color", fg="bright_magenta", bold=True)
        print(styled)
    except Exception as e:
        print(f"Error with bright_magenta: {e}")
        # Fallback
        styled = click.style("This is our primary color (fallback)", fg="magenta", bold=True)
        print(styled)


if __name__ == "__main__":
    test_click_colors()
