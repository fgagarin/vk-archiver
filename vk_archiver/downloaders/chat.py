import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..filter import check_for_duplicates
from ..functions import download_photos
from ..utils.logging_config import get_logger
from ..utils.rate_limiter import RateLimitedVKAPI
from .user import UsersPhotoDownloader

logger = get_logger("downloaders.chat")

if TYPE_CHECKING:
    from ..utils import Utils

# Global constants
DOWNLOADS_DIR = Path.cwd().joinpath("downloads")


class ChatMembersPhotoDownloader:
    """Download photos from chat members."""

    def __init__(
        self, chat_id: str, vk_instance: RateLimitedVKAPI, utils: "Utils"
    ) -> None:
        """
        Initialize ChatMembersPhotoDownloader.

        Args:
            chat_id: VK chat ID
            vk_instance: Authenticated VK API instance
            utils: Utils helper providing VK helpers and file operations
        """
        self.chat_id = int(chat_id)
        self.vk = vk_instance
        self.utils = utils

    async def main(self) -> None:
        """
        Download photos from all chat members.

        This method downloads photos from all members of a VK chat conversation:
        1. Retrieves chat information and creates chat directory
        2. Gets list of all chat members
        3. Filters out the current user from the member list
        4. Downloads photos from each member using UsersPhotoDownloader
        5. Organizes photos by chat name and member names

        Raises:
            InitializationError: If utils instance is not initialized

        Note:
            Skips empty chats and provides appropriate logging messages.
        """
        chat_title = await self.utils.get_chat_title(str(self.chat_id))
        chat_path = DOWNLOADS_DIR.joinpath(chat_title)

        # Create folder for chat members' photos if it doesn't exist
        self.utils.create_dir(chat_path)

        members_resp = await self.vk.call("messages.getChat", chat_id=self.chat_id)
        members = members_resp["users"]

        if members == []:
            logger.info("You left this chat")
            logger.info(f"Skipping download for empty chat: {chat_path}")
        else:
            members_ids = []

            for member_id in members:
                if member_id > 0:
                    members_ids.append(member_id)

            current_uid = await self.utils.get_user_id()
            members_ids.remove(current_uid)

            await UsersPhotoDownloader(
                user_ids=members_ids,
                vk_instance=self.vk,
                utils=self.utils,
                parent_dir=chat_path,
            ).main()


class ChatPhotoDownloader:
    """Download photos from chat attachments."""

    def __init__(
        self, chat_id: str, vk_instance: RateLimitedVKAPI, utils: "Utils"
    ) -> None:
        """
        Initialize ChatPhotoDownloader.

        Args:
            chat_id: VK chat ID
            vk_instance: Authenticated VK API instance
            utils: Utils helper providing VK helpers and file operations
        """
        self.chat_id = int(chat_id)
        self.vk = vk_instance
        self.utils = utils

    async def get_attachments(self) -> list[dict[str, Any]]:
        """
        Get photo attachments from chat history.

        This method retrieves all photo attachments from a VK chat conversation
        by iterating through the chat history. It processes messages sequentially
        and extracts photo attachments from each message.

        Returns:
            List of photo attachment dictionaries containing 'id', 'owner_id', 'url',
            'likes', and 'date' keys. Each dictionary represents a photo found in
            the chat history.

        Note:
            Uses VK API's getHistoryAttachments method to efficiently retrieve
            attachments from the entire chat history.
        """
        resp = await self.vk.call(
            "messages.getHistoryAttachments",
            peer_id=2000000000 + self.chat_id,
            media_type="photo",
        )
        raw_data = resp["items"]

        photos = []

        for photo in raw_data:
            photos.append(
                {
                    "id": photo["attachment"]["photo"]["id"],
                    "owner_id": photo["attachment"]["photo"]["owner_id"],
                    "url": photo["attachment"]["photo"]["sizes"][-1]["url"],
                }
            )

        return photos

    async def main(self) -> None:
        """
        Download all photo attachments from chat.

        This method downloads all photo attachments from a VK chat conversation:
        1. Retrieves chat information and creates chat directory
        2. Gets all photo attachments from chat history
        3. Downloads all photos with progress tracking
        4. Checks for and removes duplicate files
        5. Provides detailed logging of the download process

        Raises:
            InitializationError: If utils instance is not initialized

        Note:
            Photos are downloaded concurrently for better performance.
            Duplicate detection is performed after download completion.
        """
        chat_title = await self.utils.get_chat_title(str(self.chat_id))
        photos_path = DOWNLOADS_DIR.joinpath(chat_title)
        if not photos_path.exists():
            logger.info(f"Creating folder for chat photos '{chat_title}'")
            photos_path.mkdir()

        photos = await self.get_attachments()

        logger.info(
            f"Will download {len(photos)} photo{'s' if len(photos) != 1 else ''}"
        )

        time_start = time.time()

        # Download chat attachments
        await download_photos(photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logger.info(
            f"Downloaded {len(photos)} photo{'s' if len(photos) != 1 else ''} in {download_time} second{'s' if download_time != 1 else ''}"
        )

        logger.info("Checking for duplicates")
        dublicates_count = check_for_duplicates(photos_path)
        logger.info(f"Duplicates removed: {dublicates_count}")

        logger.info(
            f"Total downloaded: {len(photos) - dublicates_count} photo{'s' if len(photos) - dublicates_count != 1 else ''}"
        )


class ChatUserPhotoDownloader:
    """Download photos from user chat conversation."""

    def __init__(
        self,
        chat_id: str,
        vk_instance: RateLimitedVKAPI,
        utils: "Utils",
        parent_dir: Path = DOWNLOADS_DIR,
    ) -> None:
        """
        Initialize ChatUserPhotoDownloader.

        Args:
            chat_id: VK chat ID (user ID for direct messages)
            vk_instance: Authenticated VK API instance
            utils: Utils helper providing VK helpers and file operations
            parent_dir: Parent directory for downloads
        """
        self.chat_id = chat_id
        self.parent_dir = parent_dir
        self.vk = vk_instance
        self.utils = utils

    async def get_attachments(self) -> list[dict[str, Any]]:
        """
        Get photo attachments from user chat history.

        This method retrieves all photo attachments from a private chat conversation
        with a specific VK user by iterating through the chat history.

        Returns:
            List of photo attachment dictionaries containing 'id', 'owner_id', 'url',
            'likes', and 'date' keys. Each dictionary represents a photo found in
            the private chat history.

        Note:
            Uses VK API's getHistoryAttachments method to efficiently retrieve
            attachments from the entire private chat history.
        """
        resp = await self.vk.call(
            "messages.getHistoryAttachments", peer_id=self.chat_id, media_type="photo"
        )
        raw_data = resp["items"]

        photos = []

        for photo in raw_data:
            photos.append(
                {
                    "id": photo["attachment"]["photo"]["id"],
                    "owner_id": photo["attachment"]["photo"]["owner_id"],
                    "url": photo["attachment"]["photo"]["sizes"][-1]["url"],
                }
            )

        return photos

    async def main(self) -> None:
        """
        Download all photo attachments from user chat conversation.

        This method downloads all photo attachments from a private chat conversation
        with a specific VK user:
        1. Retrieves user information and creates user directory
        2. Gets all photo attachments from private chat history
        3. Downloads all photos with progress tracking
        4. Checks for and removes duplicate files
        5. Organizes photos by user name

        Raises:
            InitializationError: If utils instance is not initialized

        Note:
            Photos are downloaded concurrently for better performance.
            Duplicate detection is performed after download completion.
        """
        username = await self.utils.get_username(self.chat_id)

        photos_path = self.parent_dir.joinpath(f"Chat {username}")
        self.utils.create_dir(photos_path)

        photos = await self.get_attachments()

        logger.info(
            f"Will download {len(photos)} photo{'s' if len(photos) != 1 else ''}"
        )

        time_start = time.time()

        await download_photos(photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logger.info(
            f"Downloaded {len(photos)} photo{'s' if len(photos) != 1 else ''} in {download_time} second{'s' if download_time != 1 else ''}"
        )

        logger.info("Checking for duplicates")
        dublicates_count = check_for_duplicates(photos_path)
        logger.info(f"Duplicates removed: {dublicates_count}")

        logger.info(
            f"Total downloaded: {len(photos) - dublicates_count} photo{'s' if len(photos) - dublicates_count != 1 else ''}"
        )
