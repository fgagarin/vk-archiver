"""Authentication utilities for VK API."""

from typing import TYPE_CHECKING

import vk_api
from vk_api.vk_api import VkApiMethod

from .exceptions import AuthenticationError, InitializationError
from .logging_config import get_logger

logger = get_logger("utils.auth")

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
            InitializationError: If VK API is not initialized
        """
        if self._vk is None:
            raise InitializationError(
                "VK API not initialized. Run `auth_by_token` method first.",
                component="VK API",
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
            AuthenticationError: If token is missing from configuration or invalid

        Note:
            Token can be obtained from: https://vkhost.github.io/
            The method provides helpful logging messages for troubleshooting.
        """
        config = self._config_manager.get_config()

        if not config.get("token"):
            logger.error("VK access token is required")
            logger.info("Get token from: https://vkhost.github.io/")
            raise AuthenticationError(
                "VK access token is required",
                details="Token not found in configuration",
            )

        try:
            vk_session = vk_api.VkApi(token=config["token"])
            self._vk = vk_session.get_api()
            logger.info("Successfully authenticated with token.")
            return self._vk
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.info("Get token from: https://vkhost.github.io/")
            raise AuthenticationError(
                "Invalid VK access token",
                details=f"Authentication failed: {e}",
                original_exception=e,
            ) from e

    def get_user_id(self) -> int:
        """
        Get current user ID from VK API.

        This method retrieves the current user's ID from the VK API using
        the account.getProfileInfo method. It requires a valid authenticated
        VK API instance.

        Returns:
            Current user ID as an integer

        Raises:
            InitializationError: If VK API is not initialized (call auth_by_token first)
        """
        profile_info = self.vk.account.getProfileInfo()
        return int(profile_info["id"])
