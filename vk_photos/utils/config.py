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
        """Load configuration from YAML file."""
        with open(self._config_path, encoding="utf-8") as yml_file:
            self._config = yaml.load(yml_file.read(), Loader=yaml.Loader)

    def get_config(self) -> dict[str, Any]:
        """
        Get the loaded configuration.

        Returns:
            Configuration dictionary
        """
        return self._config

    def validate_config(self) -> None:
        """
        Validate configuration to ensure only token-based authentication is used.

        Raises:
            RuntimeError: If login/password fields are found in config
        """
        if "login" in self._config or "password" in self._config:
            raise RuntimeError(
                "Login/password authentication is forbidden. "
                "Only token-based authentication is allowed. "
                "Remove login and password fields from config.yaml"
            )
