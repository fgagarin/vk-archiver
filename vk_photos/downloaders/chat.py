import logging
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytils import numeral
from vk_api.vk_api import VkApiMethod

from ..filter import check_for_duplicates
from ..functions import download_photos
from .user import UsersPhotoDownloader

if TYPE_CHECKING:
    from ..main import Utils

# Global constants
DOWNLOADS_DIR = Path.cwd().joinpath("downloads")

# Global utils instance - will be set by main.py
utils: "Utils | None" = None


def set_utils_instance(utils_instance: "Utils") -> None:
    """
    Set the global utils instance.

    Args:
        utils_instance: Utils instance to set globally
    """
    global utils
    utils = utils_instance


class ChatMembersPhotoDownloader:
    """Download photos from chat members."""

    def __init__(self, chat_id: str, vk_instance: VkApiMethod) -> None:
        """
        Initialize ChatMembersPhotoDownloader.

        Args:
            chat_id: VK chat ID
            vk_instance: Authenticated VK API instance
        """
        self.chat_id = int(chat_id)
        self.vk = vk_instance

    async def main(self) -> None:
        """Download photos from all chat members."""
        if utils is None:
            raise RuntimeError("Utils instance not initialized")

        chat_title = utils.get_chat_title(str(self.chat_id))
        chat_path = DOWNLOADS_DIR.joinpath(chat_title)

        # Создаём папку с фотографиями участников беседы, если её не существует
        utils.create_dir(chat_path)

        members = self.vk.messages.getChat(chat_id=self.chat_id)["users"]

        if members == []:
            logging.info("Вы вышли из этой беседы")
            logging.info(f"Skipping download for empty chat: {chat_path}")
        else:
            members_ids = []

            for member_id in members:
                if member_id > 0:
                    members_ids.append(member_id)

            members_ids.remove(utils.get_user_id())

            await UsersPhotoDownloader(
                user_ids=members_ids, vk_instance=self.vk, parent_dir=chat_path
            ).main()


class ChatPhotoDownloader:
    """Download photos from chat attachments."""

    def __init__(self, chat_id: str, vk_instance: VkApiMethod) -> None:
        """
        Initialize ChatPhotoDownloader.

        Args:
            chat_id: VK chat ID
            vk_instance: Authenticated VK API instance
        """
        self.chat_id = int(chat_id)
        self.vk = vk_instance

    def get_attachments(self) -> list[dict[str, Any]]:
        """
        Get photo attachments from chat history.

        Returns:
            List of photo attachment data
        """
        raw_data = self.vk.messages.getHistoryAttachments(
            peer_id=2000000000 + self.chat_id, media_type="photo"
        )["items"]

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
        """Download all photo attachments from chat."""
        if utils is None:
            raise RuntimeError("Utils instance not initialized")

        chat_title = utils.get_chat_title(str(self.chat_id))
        photos_path = DOWNLOADS_DIR.joinpath(chat_title)
        if not photos_path.exists():
            logging.info(f"Создаём папку с фотографиями беседы '{chat_title}'")
            photos_path.mkdir()

        photos = self.get_attachments()

        logging.info(
            "{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
            )
        )

        time_start = time.time()

        # Скачиваем вложения беседы
        await download_photos(photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info(
            "{} {} за {}".format(
                numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд"),
            )
        )

        logging.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(photos) - dublicates_count} фото")


class ChatUserPhotoDownloader:
    """Download photos from user chat conversation."""

    def __init__(
        self, chat_id: str, vk_instance: VkApiMethod, parent_dir: Path = DOWNLOADS_DIR
    ) -> None:
        """
        Initialize ChatUserPhotoDownloader.

        Args:
            chat_id: VK chat ID (user ID for direct messages)
            vk_instance: Authenticated VK API instance
            parent_dir: Parent directory for downloads
        """
        self.chat_id = chat_id
        self.parent_dir = parent_dir
        self.vk = vk_instance

    def get_attachments(self) -> list[dict[str, Any]]:
        """
        Get photo attachments from user chat history.

        Returns:
            List of photo attachment data
        """
        raw_data = self.vk.messages.getHistoryAttachments(
            peer_id=self.chat_id, media_type="photo"
        )["items"]

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
        """Download all photo attachments from user chat conversation."""
        if utils is None:
            raise RuntimeError("Utils instance not initialized")

        username = utils.get_username(self.chat_id)

        photos_path = self.parent_dir.joinpath(f"Переписка {username}")
        utils.create_dir(photos_path)

        photos = self.get_attachments()

        logging.info(
            "{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
            )
        )

        time_start = time.time()

        await download_photos(photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info(
            "{} {} за {}".format(
                numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд"),
            )
        )

        logging.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(photos) - dublicates_count} фото")
