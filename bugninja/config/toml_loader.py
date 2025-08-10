"""
TOML configuration loader for Bugninja.

This module provides TOML-based configuration loading with validation
and default values.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import tomli


class TOMLConfigLoader:
    """Loader for TOML-based configuration files.

    This class handles loading configuration from TOML files with support for:
    - Nested configuration sections
    - Default values
    - Validation
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize TOML config loader.

        Args:
            config_path: Path to TOML configuration file. Defaults to 'bugninja.toml'
        """
        self.config_path = config_path or Path("bugninja.toml")
        self._config_cache: Optional[Dict[str, Any]] = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file.

        Returns:
            Dictionary containing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If TOML file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        # Load configuration
        config = self._load_toml_file()

        # Flatten nested configuration for easier access
        return self._flatten_config(config)

    def _load_toml_file(self) -> Dict[str, Any]:
        """Load and parse TOML configuration file.

        Returns:
            Parsed TOML configuration

        Raises:
            ValueError: If TOML file is invalid
        """
        try:
            with open(self.config_path, "rb") as f:
                return tomli.load(f)
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML configuration file: {e}")

    def _flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested configuration for easier access.

        Args:
            config: Nested configuration dictionary
            prefix: Current key prefix for nested values

        Returns:
            Flattened configuration dictionary
        """
        flattened = {}

        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self._flatten_config(value, full_key))
            else:
                # Direct assignment for non-dict values
                flattened[full_key] = value

        return flattened

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        config = self.load_config()

        # Handle dot notation for nested keys
        keys = key.split(".")
        value = config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def reload(self) -> None:
        """Clear configuration cache to force reload on next access."""
        self._config_cache = None
