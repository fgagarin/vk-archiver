"""Main VK utilities class that combines authentication, validation, and file operations."""

from pathlib import Path
from typing import TYPE_CHECKING

from vk_api.vk_api import VkApiMethod

from .auth import VKAuthenticator
from .config import ConfigManager
from .file_ops import FileOperations
from .validation import VKValidator

if TYPE_CHECKING:
    from .auth import VKAuthenticator


class Utils:
    """Main utilities class for VK API operations."""

    def __init__(self, config_path: Path) -> None:
        """
        Initialize Utils class with configuration path.

        Args:
            config_path: Path to the configuration file
        """
        self._config_manager = ConfigManager(config_path)
        self._config_manager.validate_config()

        self._authenticator = VKAuthenticator(self._config_manager)
        self._validator = VKValidator(self._authenticator)
        self._file_ops = FileOperations()

    @property
    def vk(self) -> VkApiMethod:
        """
        Get authenticated VK API instance.

        Returns:
            Authenticated VK API instance
        """
        return self._authenticator.vk

    @property
    def validator(self) -> VKValidator:
        """
        Get VK validator instance.

        Returns:
            VKValidator: VK validator instance
        """
        return self._validator

    def create_dir(self, dir_path: Path) -> None:
        """
        Create directory if it doesn't exist.

        Args:
            dir_path: Path to the directory to create
        """
        self._file_ops.create_dir(dir_path)

    def auth_by_token(self) -> VkApiMethod:
        """
        Authenticate using VK access token only.

        Returns:
            VkApiMethod: Authenticated VK API instance
        """
        return self._authenticator.auth_by_token()

    def check_user_id(self, id: str) -> bool:
        """
        Check if user with given ID exists.

        Args:
            id: VK user ID to check

        Returns:
            True if user exists, False otherwise
        """
        return self._validator.check_user_id(id)

    def check_user_ids(self, ids_list: str) -> bool:
        """
        Check if all users with given IDs exist.

        Args:
            ids_list: Comma-separated list of VK user IDs

        Returns:
            True if all users exist, False otherwise
        """
        return self._validator.check_user_ids(ids_list)

    def check_group_id(self, id: str) -> bool:
        """
        Check if group with given ID exists.

        Args:
            id: VK group ID to check

        Returns:
            True if group exists, False otherwise
        """
        return self._validator.check_group_id(id)

    def check_group_ids(self, ids_list: str) -> bool:
        """
        Check if all groups with given IDs exist.

        Args:
            ids_list: Comma-separated list of VK group IDs

        Returns:
            True if all groups exist, False otherwise
        """
        return self._validator.check_group_ids(ids_list)

    def check_chat_id(self, id: str) -> bool:
        """
        Check if chat with given ID exists.

        Args:
            id: VK chat ID to check

        Returns:
            True if chat exists, False otherwise
        """
        return self._validator.check_chat_id(id)

    def get_user_id(self) -> int:
        """
        Get current user ID from VK API.

        Returns:
            Current user ID
        """
        return self._authenticator.get_user_id()

    def get_username(self, user_id: str) -> str:
        """
        Get username by user ID.

        This method retrieves a user's full name from the VK API using their
        user ID. It combines the first and last name into a single string.

        Args:
            user_id: VK user ID to get the username for

        Returns:
            User's full name as "First Last" format

        Note:
            Uses the VK API users.get method to retrieve user information.
            Returns the combined first and last name as a string.
        """
        user = self.vk.users.get(user_id=user_id)[0]
        first_name = str(user["first_name"])
        last_name = str(user["last_name"])
        return f"{first_name} {last_name}"

    def get_group_title(self, group_id: str) -> str:
        """
        Get group title by group ID.

        This method retrieves a group's name from the VK API using their
        group ID. It sanitizes the name by replacing problematic characters
        that could cause issues in file system operations.

        Args:
            group_id: VK group ID to get the title for

        Returns:
            Group name with sanitized characters (/, |, . replaced with spaces)

        Note:
            Uses the VK API groups.getById method to retrieve group information.
            Sanitizes the name to ensure it's safe for use as a directory name.
        """
        group_info = self.vk.groups.getById(group_id=group_id)
        group_name = (
            group_info[0]["name"]
            .replace("/", " ")
            .replace("|", " ")
            .replace(".", " ")
            .strip()
        )
        return str(group_name)

    def get_chat_title(self, chat_id: str) -> str:
        """
        Get chat title by chat ID.

        This method retrieves a chat's title from the VK API using the chat ID.
        It converts the chat ID to a peer ID and uses the messages API to
        get conversation information.

        Args:
            chat_id: VK chat ID to get the title for

        Returns:
            Chat title as a string

        Note:
            Uses the VK API messages.getConversationsById method.
            Chat IDs are converted to peer IDs by adding 2000000000.
            Returns the chat_settings.title from the conversation data.
        """
        conversation = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + int(chat_id)
        )
        chat_title = conversation["items"][0]["chat_settings"]["title"]
        return str(chat_title)
