"""User photo downloader classes for VK Photos application."""

import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..functions import decline, download_photos
from ..utils.exceptions import InitializationError
from ..utils.logging_config import get_logger
from ..utils.rate_limiter import RateLimitedVKAPI

logger = get_logger("downloaders.user")

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
        self,
        user_id: str,
        vk_instance: RateLimitedVKAPI,
        parent_dir: Path = DOWNLOADS_DIR,
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

    async def get_photos(self) -> list[dict[str, Any]]:
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
            # Collect photos from saved album
            photos_saved_resp = await self.vk.call(
                "photos.get",
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="saved",
                photo_sizes=True,
                extended=True,
            )
            photos_by_saved = photos_saved_resp["items"]

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
            # Collect photos from profile
            photos_profile_resp = await self.vk.call(
                "photos.get",
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="profile",
                photo_sizes=True,
                extended=True,
            )
            photos_by_profile = photos_profile_resp["items"]

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
            # Collect photos from wall
            photos_wall_resp = await self.vk.call(
                "photos.get",
                user_id=self.user_id,
                count=100,
                offset=offset,
                album_id="wall",
                photo_sizes=True,
                extended=True,
            )
            photos_by_wall = photos_wall_resp["items"]

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
            all_resp = await self.vk.call(
                "photos.getAll",
                owner_id=self.user_id,
                count=100,
                offset=offset,
                photo_sizes=True,
                extended=True,
            )
            all_photos = all_resp["items"]

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
        user_info_list = await self.vk.call(
            "users.get", user_ids=self.user_id, fields="sex, photo_max_orig"
        )
        user_info = user_info_list[0]

        decline_username = decline(
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            sex=user_info["sex"],
        )

        if utils is None:
            raise InitializationError(
                "Utils instance not initialized", component="UserPhotoDownloader"
            )

        username = await utils.get_username(str(self.user_id))

        photos_path = self.parent_dir.joinpath(username)
        utils.create_dir(photos_path)

        # User page is deleted
        if "deactivated" in user_info:
            logger.info("This page is deleted")
            logger.info(
                f"Skipping download for deactivated user profile: {photos_path}"
            )
        else:
            # Profile is closed
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logger.info(f"Profile {decline_username} is closed :(")
                photos = [
                    {
                        "id": self.user_id,
                        "owner_id": self.user_id,
                        "url": user_info["photo_max_orig"],
                        "likes": 0,
                    }
                ]
            else:
                logger.info(f"Getting photos from {decline_username}...")

                # Get user photos
                photos = await self.get_photos()

            # Sort user photos by date
            photos.sort(key=lambda k: k["date"], reverse=True)

            logger.info(
                f"Will download {len(photos)} photo{'s' if len(photos) != 1 else ''}"
            )

            time_start = time.time()

            # Download user photos
            await download_photos(photos_path, photos)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)
            logger.info(
                f"Downloaded {len(photos)} photo{'s' if len(photos) != 1 else ''} in {download_time} second{'s' if download_time != 1 else ''}"
            )


class UsersPhotoDownloader:
    """Downloader for photos from multiple VK user profiles."""

    def __init__(
        self,
        user_ids: list[str],
        vk_instance: RateLimitedVKAPI,
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
