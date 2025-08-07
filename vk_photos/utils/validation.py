"""Validation utilities for VK API entities."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import VKAuthenticator


class VKValidator:
    """Validates VK API entities (users, groups, chats)."""

    def __init__(self, authenticator: "VKAuthenticator") -> None:
        """
        Initialize VKValidator with authenticator.

        Args:
            authenticator: VK authenticator instance
        """
        self._authenticator = authenticator

    def check_user_id(self, id: str) -> bool:
        """
        Check if user with given ID exists.

        Args:
            id: VK user ID to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            # Проверяем, существует ли пользователь с таким id
            user = self._authenticator.vk.users.get(user_ids=int(id))
            return len(user) != 0
        except Exception:
            return False

    def check_user_ids(self, ids_list: str) -> bool:
        """
        Check if all users with given IDs exist.

        Args:
            ids_list: Comma-separated list of VK user IDs

        Returns:
            True if all users exist, False otherwise
        """
        try:
            for user_id in ids_list.split(","):
                if not self.check_user_id(user_id):
                    return False
            return True
        except Exception:
            return False

    def check_group_id(self, id: str) -> bool:
        """
        Check if group with given ID exists.

        Args:
            id: VK group ID to check

        Returns:
            True if group exists, False otherwise
        """
        try:
            # Проверяем, существует ли группа с таким id
            group = self._authenticator.vk.groups.getById(group_id=int(id))
            if len(group) != 0:
                return True
            return False
        except Exception as e:
            print(e)
            return False

    def check_group_ids(self, ids_list: str) -> bool:
        """
        Check if all groups with given IDs exist.

        Args:
            ids_list: Comma-separated list of VK group IDs

        Returns:
            True if all groups exist, False otherwise
        """
        try:
            for group_id in ids_list.split(","):
                if not self.check_group_id(group_id):
                    return False
            return True
        except Exception:
            return False

    def check_chat_id(self, id: str) -> bool:
        """
        Check if chat with given ID exists.

        Args:
            id: VK chat ID to check

        Returns:
            True if chat exists, False otherwise
        """
        try:
            # Проверяем, существует ли беседа с таким id
            conversation = self._authenticator.vk.messages.getConversationsById(
                peer_ids=2000000000 + int(id)
            )
            if conversation["count"] != 0:
                return True
            return False
        except Exception:
            return False
