"""Configuration management utilities."""

from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Manages application configuration loading and validation."""

    def __init__(self, config_path: Path) -> None:
        """
        Initialize ConfigManager with config file path.

        Args:
            config_path: Path to the configuration file
        """
        self._config_path = config_path
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """
        Load configuration from YAML file.

        This method reads the configuration file specified during initialization
        and loads it into the internal configuration dictionary. The file is
        expected to be in YAML format with UTF-8 encoding.

        Note:
            Called automatically during ConfigManager initialization.
            The configuration file should contain VK API authentication settings.
        """
        with open(self._config_path, encoding="utf-8") as yml_file:
            self._config = yaml.load(yml_file.read(), Loader=yaml.Loader)

    def get_config(self) -> dict[str, Any]:
        """
        Get the loaded configuration.

        This method returns the complete configuration dictionary that was
        loaded from the YAML file during initialization.

        Returns:
            Configuration dictionary containing all settings from the config file

        Note:
            The configuration typically contains VK API authentication settings
            such as access tokens and other application-specific parameters.
        """
        return self._config

    def validate_config(self) -> None:
        """
        Validate configuration to ensure only token-based authentication is used.

        This method validates the loaded configuration to ensure it follows
        security best practices by using only token-based authentication.
        It explicitly forbids the use of login/password combinations for
        security reasons.

        Raises:
            RuntimeError: If login or password fields are found in the configuration

        Note:
            Token-based authentication is more secure and recommended for
            VK API applications. Login/password authentication is deprecated
            and potentially unsafe.
        """
        if "login" in self._config or "password" in self._config:
            raise RuntimeError(
                "Login/password authentication is forbidden. "
                "Only token-based authentication is allowed. "
                "Remove login and password fields from config.yaml"
            )
