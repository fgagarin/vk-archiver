"""Validation utilities for VK API entities."""

from typing import TYPE_CHECKING

from .exceptions import APIError, ResourceNotFoundError, ValidationError

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

        This method verifies that a VK user with the specified ID exists and is
        accessible via the VK API. It attempts to retrieve user information
        and returns True if the user is found.

        Args:
            id: VK user ID to check

        Returns:
            True if user exists and is accessible, False otherwise

        Note:
            Returns False for any API errors, including invalid IDs, deleted
            accounts, or network issues.
        """
        try:
            # Check if user with this id exists
            user = self._authenticator.vk.users.get(user_ids=int(id))
            return len(user) != 0
        except (ValueError, TypeError):
            # Invalid ID format
            return False
        except Exception:
            # Any other API or network error
            return False

    def validate_user_id(self, id: str) -> None:
        """
        Validate that user with given ID exists.

        This method verifies that a VK user with the specified ID exists and is
        accessible via the VK API. It raises specific exceptions for different
        error scenarios.

        Args:
            id: VK user ID to validate

        Raises:
            ValidationError: If user ID format is invalid
            ResourceNotFoundError: If user with given ID does not exist
            APIError: If VK API call fails
        """
        try:
            user_id = int(id)
        except ValueError as e:
            raise ValidationError(
                f"Invalid user ID format: {id}",
                details="User ID must be a valid integer",
                original_exception=e,
            ) from e

        try:
            user = self._authenticator.vk.users.get(user_ids=user_id)
            if len(user) == 0:
                raise ResourceNotFoundError(
                    f"User with ID {id} does not exist",
                    resource_type="user",
                    resource_id=id,
                )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise APIError(
                f"Failed to validate user ID: {id}",
                details=f"VK API error: {e}",
                original_exception=e,
                api_method="users.get",
            ) from e

    def check_user_ids(self, ids_list: str) -> bool:
        """
        Check if all users with given IDs exist.

        This method verifies that all VK users in a comma-separated list exist
        and are accessible. It checks each user ID individually and returns
        True only if all users are found.

        Args:
            ids_list: Comma-separated list of VK user IDs to check

        Returns:
            True if all users exist and are accessible, False if any user
            is not found or inaccessible

        Note:
            Stops checking at the first invalid user ID for efficiency.
        """
        try:
            for user_id in ids_list.split(","):
                if not self.check_user_id(user_id):
                    return False
            return True
        except Exception:
            # Any parsing or iteration error
            return False

    def check_group_id(self, id: str) -> bool:
        """
        Check if group with given ID exists.

        This method verifies that a VK group with the specified ID exists and is
        accessible via the VK API. It attempts to retrieve group information
        and returns True if the group is found.

        Args:
            id: VK group ID to check

        Returns:
            True if group exists and is accessible, False otherwise

        Note:
            Returns False for any API errors, including invalid IDs, deleted
            groups, or network issues. Prints error details for debugging.
        """
        try:
            # Check if group with this id exists
            group = self._authenticator.vk.groups.getById(group_id=int(id))
            if len(group) != 0:
                return True
            return False
        except (ValueError, TypeError):
            # Invalid ID format
            return False
        except Exception:
            # Any other API or network error
            return False

    def validate_group_id(self, id: str) -> None:
        """
        Validate that group with given ID exists.

        This method verifies that a VK group with the specified ID exists and is
        accessible via the VK API. It raises specific exceptions for different
        error scenarios.

        Args:
            id: VK group ID to validate

        Raises:
            ValidationError: If group ID format is invalid
            ResourceNotFoundError: If group with given ID does not exist
            APIError: If VK API call fails
        """
        try:
            group_id = int(id)
        except ValueError as e:
            raise ValidationError(
                f"Invalid group ID format: {id}",
                details="Group ID must be a valid integer",
                original_exception=e,
            ) from e

        try:
            group = self._authenticator.vk.groups.getById(group_id=group_id)
            if len(group) == 0:
                raise ResourceNotFoundError(
                    f"Group with ID {id} does not exist",
                    resource_type="group",
                    resource_id=id,
                )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise APIError(
                f"Failed to validate group ID: {id}",
                details=f"VK API error: {e}",
                original_exception=e,
                api_method="groups.getById",
            ) from e

    def check_group_ids(self, ids_list: str) -> bool:
        """
        Check if all groups with given IDs exist.

        This method verifies that all VK groups in a comma-separated list exist
        and are accessible. It checks each group ID individually and returns
        True only if all groups are found.

        Args:
            ids_list: Comma-separated list of VK group IDs to check

        Returns:
            True if all groups exist and are accessible, False if any group
            is not found or inaccessible

        Note:
            Stops checking at the first invalid group ID for efficiency.
        """
        try:
            for group_id in ids_list.split(","):
                if not self.check_group_id(group_id):
                    return False
            return True
        except Exception:
            # Any parsing or iteration error
            return False

    def check_chat_id(self, id: str) -> bool:
        """
        Check if chat with given ID exists.

        This method verifies that a VK chat with the specified ID exists and is
        accessible via the VK API. It attempts to retrieve chat information
        using the messages.getConversationsById method.

        Args:
            id: VK chat ID to check

        Returns:
            True if chat exists and is accessible, False otherwise

        Note:
            Returns False for any API errors, including invalid IDs, deleted
            chats, or network issues. Chat IDs are converted to peer_ids
            by adding 2000000000.
        """
        try:
            # Check if chat with this id exists
            conversation = self._authenticator.vk.messages.getConversationsById(
                peer_ids=2000000000 + int(id)
            )
            if conversation["count"] != 0:
                return True
            return False
        except (ValueError, TypeError):
            # Invalid ID format
            return False
        except Exception:
            # Any other API or network error
            return False

    def validate_chat_id(self, id: str) -> None:
        """
        Validate that chat with given ID exists.

        This method verifies that a VK chat with the specified ID exists and is
        accessible via the VK API. It raises specific exceptions for different
        error scenarios.

        Args:
            id: VK chat ID to validate

        Raises:
            ValidationError: If chat ID format is invalid
            ResourceNotFoundError: If chat with given ID does not exist
            APIError: If VK API call fails
        """
        try:
            chat_id = int(id)
        except ValueError as e:
            raise ValidationError(
                f"Invalid chat ID format: {id}",
                details="Chat ID must be a valid integer",
                original_exception=e,
            ) from e

        try:
            # Chat IDs are converted to peer_ids by adding 2000000000
            peer_id = 2000000000 + chat_id
            conversation = self._authenticator.vk.messages.getConversationsById(
                peer_ids=peer_id
            )
            if conversation["count"] == 0:
                raise ResourceNotFoundError(
                    f"Chat with ID {id} does not exist",
                    resource_type="chat",
                    resource_id=id,
                )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise APIError(
                f"Failed to validate chat ID: {id}",
                details=f"VK API error: {e}",
                original_exception=e,
                api_method="messages.getConversationsById",
            ) from e
