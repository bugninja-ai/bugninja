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
            Dict[str, Any]: Parsed TOML configuration

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
            config (Dict[str, Any]): Nested configuration dictionary
            prefix (str): Current key prefix for nested values

        Returns:
            Dict[str, Any]: Flattened configuration dictionary
        """
        flattened = {}

        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Handle secrets section specially - flatten with "secrets." prefix
                if key == "secrets":
                    for secret_key, secret_value in value.items():
                        flattened[f"secrets.{secret_key}"] = secret_value
                # Handle I/O schema section specially - keep as nested dictionary
                elif key == "io_schema" and prefix == "task":
                    flattened[full_key] = value
                # Handle I/O schema sections specially - keep as nested dictionaries
                elif key in ["input_schema", "output_schema"] and prefix == "task":
                    flattened[full_key] = value
                else:
                    # Recursively flatten nested dictionaries
                    flattened.update(self._flatten_config(value, full_key))
            else:
                # Direct assignment for non-dict values
                flattened[full_key] = value

        return flattened

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value.

        Args:
            key (str): Configuration key (supports dot notation for nested keys)
            default (Any): Default value if key doesn't exist

        Returns:
            Any: Configuration value or default

        Example:
            ```python
            loader = TOMLConfigLoader()

            # Get simple value
            value = loader.get_value("llm.provider")

            # Get nested value with default
            value = loader.get_value("llm.azure_openai.api_version", "2024-02-15-preview")
            ```
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
        """Clear configuration cache to force reload on next access.

        This method clears the internal configuration cache, forcing the
        configuration to be reloaded from the TOML file on the next access.
        """
        self._config_cache = None
