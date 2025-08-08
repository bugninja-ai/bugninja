#!/usr/bin/env python3
"""
Main entry point for Bugninja CLI.

This module provides the entry point for the spectacular
Click-based CLI interface accessible via 'uv run bugninja'.
"""

from bugninja_cli.main import cli

# Export the CLI function for the entry point
__all__ = ["cli"]

if __name__ == "__main__":
    cli()
