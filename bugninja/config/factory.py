"""
Configuration factory for managing settings instances.

This module provides a factory pattern for creating and managing configuration
instances with TOML-based configuration and singleton behavior.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from bugninja.config.settings import BugninjaSettings, LLMProvider
from bugninja.config.toml_loader import TOMLConfigLoader


class ConfigurationFactory:
    """Factory for creating and managing configuration instances.

    This class provides a singleton pattern for configuration management
    with TOML-based configuration and validation.
    """

    _instance: Optional[BugninjaSettings] = None
    _toml_loader: Optional[TOMLConfigLoader] = None

    @classmethod
    def get_settings(cls, cli_mode: bool = False) -> BugninjaSettings:
        """Get or create settings instance based on CLI mode.

        Args:
            cli_mode (bool): Whether to use CLI mode (TOML) or Library mode (env vars)

        Returns:
            Configured settings instance

        Raises:
            ValueError: If configuration is invalid
        """
        # Check if we need to create a new instance
        if cls._instance is None:
            if cli_mode:
                # CLI mode: Use TOML configuration exclusively
                cls._instance = cls._load_from_toml_only()
            else:
                # Library mode: Use environment variables exclusively
                cls._instance = cls._load_from_env_only()

        return cls._instance

    @classmethod
    def _load_from_toml_only(cls) -> BugninjaSettings:
        """Load configuration from TOML file (CLI mode only).

        In CLI mode, we use TOML for non-sensitive settings (provider, model, temperature)
        but still load sensitive data (API keys, endpoints) from environment variables.

        Returns:
            BugninjaSettings: Settings loaded from TOML + environment variables

        Raises:
            ValueError: If TOML configuration is invalid
        """
        # Initialize TOML loader if needed
        if cls._toml_loader is None:
            cls._toml_loader = TOMLConfigLoader()

        try:
            # Load TOML configuration
            toml_config = cls._toml_loader.load_config()
            toml_overrides = cls._convert_toml_to_pydantic(toml_config)

            # Create settings with TOML values + environment variables
            # This ensures API keys and endpoints come from env vars (security)
            return BugninjaSettings(**toml_overrides)
        except Exception as e:
            raise ValueError(f"TOML configuration error: {str(e)}")

    @classmethod
    def _load_from_env_only(cls) -> BugninjaSettings:
        """Load configuration from environment variables (Library mode only).

        Returns:
            BugninjaSettings: Settings loaded from environment variables

        Raises:
            ValueError: If environment configuration is invalid
        """
        try:
            # Create settings with environment variables only
            return BugninjaSettings()  # type: ignore
        except Exception as e:
            raise ValueError(f"Environment configuration error: {str(e)}")

    @classmethod
    def _convert_toml_to_pydantic(cls, toml_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TOML configuration to Pydantic-compatible format.

        Args:
            toml_config: Flattened TOML configuration

        Returns:
            Dictionary compatible with Pydantic Settings
        """
        field_mapping = {
            # Project configuration
            "project.name": "project_name",
            # LLM configuration
            "llm.provider": "llm_provider",
            "llm.temperature": "llm_temperature",
            # Azure OpenAI configuration
            "llm.azure_openai.api_version": "azure_openai_api_version",
            # OpenAI configuration
            "llm.openai.base_url": "openai_base_url",
            # Anthropic configuration
            "llm.anthropic.base_url": "anthropic_base_url",
            # Google Gemini configuration
            "llm.google_gemini.base_url": "google_base_url",
            # DeepSeek configuration
            "llm.deepseek.base_url": "deepseek_base_url",
            # Ollama configuration
            "llm.ollama.base_url": "ollama_base_url",
            # Logging configuration
            "logging.level": "log_level",
            "logging.format": "log_format",
            "logging.enable_rich_logging": "enable_rich_logging",
            # Development configuration
            "development.debug_mode": "debug_mode",
            # Paths configuration
            "paths.output_base_dir": "output_base_dir",
            "paths.traversals_dir": "traversals_dir",
            "paths.screenshots_dir": "screenshots_dir",
            "paths.tasks_dir": "tasks_dir",
            # Events configuration
            "events.publishers": "event_publishers",
        }

        pydantic_config = {}
        for toml_key, field_name in field_mapping.items():
            if toml_key in toml_config:
                value = toml_config[toml_key]

                # Handle special cases
                if toml_key == "llm.provider" and isinstance(value, str):
                    # Convert string to LLMProvider enum
                    try:
                        value = LLMProvider(value)
                    except ValueError:
                        # Skip invalid provider values
                        continue
                elif toml_key.startswith("paths.") and isinstance(value, str):
                    # Convert string paths to Path objects
                    from pathlib import Path

                    value = Path(value)

                pydantic_config[field_name] = value

        # Add environment variable fallbacks for base URLs
        config_name_env_var_assoc: Dict[str, str] = {
            "openai_base_url": "OPENAI_BASE_URL",
            "anthropic_base_url": "ANTHROPIC_BASE_URL",
            "google_base_url": "GOOGLE_BASE_URL",
            "deepseek_base_url": "DEEPSEEK_BASE_URL",
            "ollama_base_url": "OLLAMA_BASE_URL",
        }

        for config_name, env_Var_name in config_name_env_var_assoc.items():
            if config_name not in pydantic_config and os.getenv(env_Var_name):
                pydantic_config[config_name] = os.getenv(env_Var_name)

        return pydantic_config

    @classmethod
    def load_task_config(cls, task_config_path: Path) -> Dict[str, Any]:
        """Load task-specific configuration from TOML file.

        Args:
            task_config_path: Path to the task_{name}.toml file

        Returns:
            Dictionary containing task-specific configuration

        Raises:
            FileNotFoundError: If task config file doesn't exist
            ValueError: If TOML file is malformed or invalid
        """
        if not task_config_path.exists():
            raise FileNotFoundError(f"Task configuration file not found: {task_config_path}")

        # Load and validate TOML
        toml_loader = TOMLConfigLoader(task_config_path)
        try:
            config = toml_loader.load_config()
        except Exception as e:
            raise ValueError(f"Invalid TOML configuration file '{task_config_path}': {str(e)}")

        # Validate required fields (config is flattened by TOMLConfigLoader)
        if not config.get("task.name"):
            raise ValueError(
                f"Missing required field 'task.name' in configuration file '{task_config_path}'"
            )
        if not config.get("task.description"):
            raise ValueError(
                f"Missing required field 'task.description' in configuration file '{task_config_path}'"
            )

        # Extract secrets from flattened config
        secrets: Dict[str, str] = {}
        for key, value in config.items():
            if key.startswith("secrets."):
                secret_key = key.replace("secrets.", "")
                secrets[secret_key] = value

        # Add secrets to config if any exist
        if secrets:
            config["task_secrets"] = secrets

        return config

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing).

        This method clears the cached settings instance and TOML loader, forcing
        a new instance to be created on the next get_settings() call.
        """
        cls._instance = None
        cls._toml_loader = None
