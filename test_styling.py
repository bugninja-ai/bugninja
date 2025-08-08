#!/usr/bin/env python3
"""
Test script to check if CLI styling is working.
"""

from bugninja_cli.themes.colors import (
    echo_error,
    echo_info,
    echo_primary,
    echo_success,
    echo_warning,
)
from bugninja_cli.utils.ascii_art import (
    display_banner,
    get_operation_icon,
    get_status_icon,
)


def test_styling():
    """Test all styling functions."""
    print("Testing CLI styling...")
    print()

    # Test banner
    print("=== Banner ===")
    display_banner()
    print()

    # Test colored messages
    print("=== Colored Messages ===")
    echo_success("This is a success message!")
    echo_error("This is an error message!")
    echo_warning("This is a warning message!")
    echo_info("This is an info message!")
    echo_primary("This is a primary message!")
    print()

    # Test icons
    print("=== Icons ===")
    print(f"Success icon: {get_status_icon('success')}")
    print(f"Error icon: {get_status_icon('error')}")
    print(f"Warning icon: {get_status_icon('warning')}")
    print(f"Run operation icon: {get_operation_icon('run')}")
    print(f"Replay operation icon: {get_operation_icon('replay')}")
    print()

    print("Styling test completed!")


if __name__ == "__main__":
    test_styling()
