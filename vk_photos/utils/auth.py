"""Authentication utilities for VK API."""

import logging
from typing import TYPE_CHECKING

import vk_api
from vk_api.vk_api import VkApiMethod

if TYPE_CHECKING:
    from .config import ConfigManager


class VKAuthenticator:
    """Handles VK API authentication using token-based authentication."""

    def __init__(self, config_manager: "ConfigManager") -> None:
        """
        Initialize VKAuthenticator with configuration manager.

        Args:
            config_manager: Configuration manager instance
        """
        self._config_manager = config_manager
        self._vk: VkApiMethod | None = None

    @property
    def vk(self) -> VkApiMethod:
        """
        Get authenticated VK API instance.

        Returns:
            Authenticated VK API instance

        Raises:
            RuntimeError: If VK API is not initialized
        """
        if self._vk is None:
            raise RuntimeError(
                "VK API not initialized. Run `auth_by_token` method first."
            )
        return self._vk

    def auth_by_token(self) -> VkApiMethod:
        """
        Authenticate using VK access token only.

        This method authenticates with the VK API using a token-based approach.
        It validates that a token is present in the configuration and attempts
        to create a VK API session. The token should be obtained from the
        VK application settings.

        Returns:
            VkApiMethod: Authenticated VK API instance

        Raises:
            RuntimeError: If token is missing from configuration or invalid

        Note:
            Token can be obtained from: https://vkhost.github.io/
            The method provides helpful logging messages for troubleshooting.
        """
        config = self._config_manager.get_config()

        if not config.get("token"):
            logging.error("VK access token is required")
            logging.info("Get token from: https://vkhost.github.io/")
            raise RuntimeError("VK access token is required")

        try:
            vk_session = vk_api.VkApi(token=config["token"])
            self._vk = vk_session.get_api()
            logging.info("Successfully authenticated with token.")
            return self._vk
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            logging.info("Get token from: https://vkhost.github.io/")
            raise RuntimeError("Invalid VK access token") from e

    def get_user_id(self) -> int:
        """
        Get current user ID from VK API.

        This method retrieves the current user's ID from the VK API using
        the account.getProfileInfo method. It requires a valid authenticated
        VK API instance.

        Returns:
            Current user ID as an integer

        Raises:
            RuntimeError: If VK API is not initialized (call auth_by_token first)
        """
        profile_info = self.vk.account.getProfileInfo()
        return int(profile_info["id"])
