"""User photo downloader classes for VK Photos application."""

import logging
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytils import numeral
from vk_api.vk_api import VkApiMethod

from ..functions import decline, download_photos
from ..utils.exceptions import (
    InitializationError,
)

if TYPE_CHECKING:
    from ..utils import Utils

# Global constants
DOWNLOADS_DIR = Path.cwd().joinpath("downloads")

# Global utils instance - will be imported from main
utils: "Utils | None" = None


def set_utils_instance(utils_instance: "Utils") -> None:
    """
    Set the global utils instance.

    Args:
        utils_instance: Utils instance to set globally
    """
    global utils
    utils = utils_instance


class UserPhotoDownloader:
    """Downloader for photos from a single VK user profile."""

    def __init__(
        self, user_id: str, vk_instance: VkApiMethod, parent_dir: Path = DOWNLOADS_DIR
    ) -> None:
        """
        Initialize UserPhotoDownloader.

        Args:
            user_id: VK user ID to download photos from
            vk_instance: VK API instance
            parent_dir: Parent directory for downloads
        """
        self.user_id = user_id
        self.vk = vk_instance
        self.parent_dir = parent_dir

    def get_photos(self) -> list[dict[str, Any]]:
        """
        Get all photos from user profile.

        This method retrieves all photos from a VK user's profile, including:
        - Saved photos (saved album)
        - Profile photos (profile album)
        - Wall photos (wall album)
        - All photos (getAll method)

        Returns:
            List of photo dictionaries containing 'id', 'owner_id', 'url', 'likes', and 'date' keys.
            Photos are sorted by date in descending order.

        Note:
            Each photo dictionary contains the highest resolution URL available.
        """
        photos: list[dict[str, Any]] = []

        offset = 0
        while True:
            # Собираем фото с сохраненок
            photos_by_saved = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="saved",
                photo_sizes=True,
                extended=True,
            )["items"]

            raw_data = photos_by_saved  # photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append(
                    {
                        "id": photo["id"],
                        "owner_id": photo["owner_id"],
                        "url": photo["sizes"][-1]["url"],
                        "likes": photo["likes"]["count"],
                        "date": photo["date"],
                    }
                )

            if len(raw_data) < 100:
                break
            offset += 100

        offset = 0
        while True:
            # Собираем фото с профиля
            photos_by_profile = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="profile",
                photo_sizes=True,
                extended=True,
            )["items"]

            raw_data = photos_by_profile  # photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append(
                    {
                        "id": photo["id"],
                        "owner_id": photo["owner_id"],
                        "url": photo["sizes"][-1]["url"],
                        "likes": photo["likes"]["count"],
                        "date": photo["date"],
                    }
                )

            if len(raw_data) < 100:
                break
            offset += 100

        offset = 0
        while True:
            # Собираем фото со стены
            photos_by_wall = self.vk.photos.get(
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="wall",
                photo_sizes=True,
                extended=True,
            )["items"]

            raw_data = photos_by_wall  # photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append(
                    {
                        "id": photo["id"],
                        "owner_id": photo["owner_id"],
                        "url": photo["sizes"][-1]["url"],
                        "likes": photo["likes"]["count"],
                        "date": photo["date"],
                    }
                )

            if len(raw_data) < 100:
                break
            offset += 100

        offset = 0
        while True:
            all_photos = self.vk.photos.getAll(
                owner_id=self.user_id,
                count=100,
                offset=offset,
                photo_sizes=True,
                extended=True,
            )["items"]

            raw_data = all_photos  # photos_by_wall + photos_by_profile

            for photo in raw_data:
                photos.append(
                    {
                        "id": photo["id"],
                        "owner_id": photo["owner_id"],
                        "url": photo["sizes"][-1]["url"],
                        "likes": photo["likes"]["count"],
                        "date": photo["date"],
                    }
                )

            if len(raw_data) < 100:
                break
            offset += 100

        return photos

    async def main(self) -> None:
        """
        Main method to download photos from user profile.

        This method orchestrates the entire photo downloading process for a single user:
        1. Retrieves user information including name and profile status
        2. Creates appropriate directory structure
        3. Handles deactivated or closed profiles gracefully
        4. Downloads all available photos with progress tracking
        5. Provides detailed logging of the download process

        Raises:
            RuntimeError: If utils instance is not initialized
        """
        user_info = self.vk.users.get(
            user_ids=self.user_id, fields="sex, photo_max_orig"
        )[0]

        decline_username = decline(
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            sex=user_info["sex"],
        )

        if utils is None:
            raise InitializationError(
                "Utils instance not initialized", component="UserPhotoDownloader"
            )

        username = utils.get_username(str(self.user_id))

        photos_path = self.parent_dir.joinpath(username)
        utils.create_dir(photos_path)

        # Страница пользователя удалена
        if "deactivated" in user_info:
            logging.info("Эта страница удалена")
            logging.info(
                f"Skipping download for deactivated user profile: {photos_path}"
            )
        else:
            # Профиль закрыт
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logging.info(f"Профиль {decline_username} закрыт :(")
                photos = [
                    {
                        "id": self.user_id,
                        "owner_id": self.user_id,
                        "url": user_info["photo_max_orig"],
                        "likes": 0,
                    }
                ]
            else:
                logging.info(f"Получаем фотографии {decline_username}...")

                # Получаем фотографии пользователя
                photos = self.get_photos()

            # Сортируем фотографии пользователя по дате
            photos.sort(key=lambda k: k["date"], reverse=True)

            logging.info(
                "{} {} {}".format(
                    numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                    numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                    numeral.get_plural(
                        len(photos), "фотография, фотографии, фотографий"
                    ),
                )
            )

            time_start = time.time()

            # Скачиваем фотографии пользователя
            await download_photos(photos_path, photos)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)
            logging.info(
                "{} {} за {}".format(
                    numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                    numeral.get_plural(
                        len(photos), "фотография, фотографии, фотографий"
                    ),
                    numeral.get_plural(download_time, "секунду, секунды, секунд"),
                )
            )


class UsersPhotoDownloader:
    """Downloader for photos from multiple VK user profiles."""

    def __init__(
        self,
        user_ids: list[str],
        vk_instance: VkApiMethod,
        parent_dir: Path = DOWNLOADS_DIR,
    ) -> None:
        """
        Initialize UsersPhotoDownloader.

        Args:
            user_ids: List of VK user IDs to download photos from
            vk_instance: VK API instance
            parent_dir: Parent directory for downloads
        """
        self.user_ids = list(user_ids)
        self.vk = vk_instance
        self.parent_dir = parent_dir

    async def main(self) -> None:
        """
        Main method to download photos from multiple user profiles.

        This method downloads photos from all specified user profiles sequentially.
        Each user's photos are downloaded using the UserPhotoDownloader class
        and organized in separate directories by user name.

        Note:
            Downloads are processed one user at a time to avoid overwhelming
            the VK API and to provide clear progress tracking.
        """
        for user_id in self.user_ids:
            await UserPhotoDownloader(user_id, self.vk, self.parent_dir).main()
