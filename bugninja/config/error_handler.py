"""
Configuration error handling utilities.

This module provides centralized error handling for configuration issues,
eliminating duplication in error message generation and validation.
"""

from typing import Dict, List

from bugninja.config.provider_registry import ProviderRegistry
from bugninja.config.settings import BugninjaSettings, LLMProvider


class ConfigurationErrorHandler:
    """Handle configuration errors with provider-specific messages."""

    @staticmethod
    def get_missing_env_error(provider: LLMProvider) -> str:
        """Generate appropriate error message for missing environment variables."""
        config = ProviderRegistry.get_config(provider)
        if not config.required_env_vars:
            return f"Configuration error for {config.name}"

        env_vars_str = ", ".join(config.required_env_vars)
        return f"Missing required environment variables for {config.name}: {env_vars_str}"

    @staticmethod
    def validate_provider_config(provider: LLMProvider, settings: BugninjaSettings) -> None:
        """Validate provider configuration and raise appropriate error if invalid."""
        config = ProviderRegistry.get_config(provider)

        if not config.validate_requirements(settings):
            raise ValueError(ConfigurationErrorHandler.get_missing_env_error(provider))

    @staticmethod
    def get_provider_validation_errors(settings: BugninjaSettings) -> Dict[LLMProvider, List[str]]:
        """Get validation errors for all providers."""
        errors: Dict[LLMProvider, List[str]] = {}

        for provider in ProviderRegistry.get_supported_providers():
            config = ProviderRegistry.get_config(provider)
            provider_errors = []

            for env_var in config.required_env_vars:
                if not hasattr(settings, env_var) or getattr(settings, env_var) is None:
                    provider_errors.append(f"Missing {env_var}")

            if provider_errors:
                errors[provider] = provider_errors

        return errors

    @staticmethod
    def get_working_providers(settings: BugninjaSettings) -> List[LLMProvider]:
        """Get list of providers that have valid configuration."""
        working_providers = []

        for provider in ProviderRegistry.get_supported_providers():
            config = ProviderRegistry.get_config(provider)
            if config.validate_requirements(settings):
                working_providers.append(provider)

        return working_providers

    @staticmethod
    def format_configuration_summary(settings: BugninjaSettings) -> str:
        """Format a summary of configuration status for all providers."""
        working_providers = ConfigurationErrorHandler.get_working_providers(settings)
        validation_errors = ConfigurationErrorHandler.get_provider_validation_errors(settings)

        summary_lines = ["Configuration Summary:"]

        # Add working providers
        if working_providers:
            provider_names = [ProviderRegistry.get_config(p).name for p in working_providers]
            summary_lines.append(f"✅ Working providers: {', '.join(provider_names)}")
        else:
            summary_lines.append("❌ No providers configured")

        # Add error details
        if validation_errors:
            summary_lines.append("\nConfiguration Errors:")
            for provider, errors in validation_errors.items():
                config = ProviderRegistry.get_config(provider)
                summary_lines.append(f"  {config.name}: {', '.join(errors)}")

        return "\n".join(summary_lines)
