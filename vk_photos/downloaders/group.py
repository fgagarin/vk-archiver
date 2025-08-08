"""Group photo downloader classes for VK Photos application."""

import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..functions import download_photos, download_videos, dump
from ..utils.logging_config import get_logger
from ..utils.rate_limiter import RateLimitedVKAPI

if TYPE_CHECKING:
    from ..utils import Utils

logger = get_logger("downloaders.group")

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


class GroupAlbumsDownloader:
    """Downloader for albums from a VK group."""

    def __init__(self, group_id: str, vk_instance: RateLimitedVKAPI) -> None:
        """
        Initialize GroupAlbumsDownloader.

        Args:
            group_id: VK group ID to download albums from
            vk_instance: VK API instance
        """
        self.group_id = int(group_id)
        self.vk = vk_instance

    async def main(self) -> None:
        """
        Download all albums from the group.

        This method downloads all photos from all albums of a VK group:
        1. Retrieves group information and creates group directory
        2. Gets list of all albums in the group
        3. For each album, creates album directory and downloads all photos
        4. Saves group and album metadata as YAML files
        5. Organizes photos by group name and album name

        Note:
            Photos are downloaded with full metadata including likes and dates.
            Group and album information is preserved in info.yaml files.
        """
        group_info_list = await self.vk.call("groups.getById", group_id=self.group_id)
        group_info = group_info_list[0]
        group_name = (
            group_info["name"]
            .replace("/", " ")
            .replace("|", " ")
            .replace(".", " ")
            .strip()
        )

        group_dir = DOWNLOADS_DIR.joinpath(group_name)
        if utils is not None:
            utils.create_dir(group_dir)
        dump(group_info, group_dir.joinpath("info.yaml"))

        albums_resp = await self.vk.call("photos.getAlbums", owner_id=-self.group_id)
        albums = albums_resp["items"]

        for album in albums:
            aid = album["id"]
            album_name = album["title"]
            album_dir = group_dir.joinpath(album_name)
            if utils is not None:
                utils.create_dir(album_dir)
            dump(album, album_dir.joinpath("info.yaml"))

            photos: list[dict[str, Any]] = []
            offset = 0
            while True:
                album_resp = await self.vk.call(
                    "photos.get",
                    owner_id=-self.group_id,
                    album_id=aid,
                    count=100,
                    offset=offset,
                    photo_sizes=True,
                    extended=True,
                )
                album_photos = album_resp["items"]

                for photo in album_photos:
                    photos.append(
                        {
                            "id": photo["id"],
                            "owner_id": photo["owner_id"],
                            "url": photo["sizes"][-1]["url"],
                            "likes": photo["likes"]["count"],
                            "date": photo["date"],
                        }
                    )

                if len(album_photos) < 100:
                    break
                offset += 100

            await download_photos(album_dir, photos)


class GroupPhotoDownloader:
    """Downloader for photos from a single VK group wall."""

    def __init__(self, group_id: str, vk_instance: RateLimitedVKAPI) -> None:
        """
        Initialize GroupPhotoDownloader.

        Args:
            group_id: VK group ID to download photos from
            vk_instance: VK API instance
        """
        self.group_id = int(group_id)
        self.vk = vk_instance

    async def get_photos(self, download_videos: str) -> None:
        """
        Get photos from group wall.

        This method retrieves all photos and optionally videos from a group's wall posts.
        It processes posts sequentially, handling both regular posts and reposts,
        and extracts photo attachments from each post.

        Args:
            download_videos: Whether to download videos ("1" for yes, "2" for no)

        Note:
            - Skips posts marked as advertisements
            - Handles reposts by processing copy_history
            - Collects videos separately if download_videos is enabled
        """
        offset = 0
        while True:
            wall_resp = await self.vk.call(
                "wall.get", owner_id=-self.group_id, count=100, offset=offset
            )
            posts = wall_resp["items"]
            for post in posts:
                # Skip ad posts
                if post["marked_as_ads"]:
                    continue

                # If post is copied from another group
                if "copy_history" in post:
                    if "attachments" in post["copy_history"][0]:
                        self.get_single_post(post["copy_history"][0])

                elif "attachments" in post:
                    self.get_single_post(post)

            if len(posts) < 100:
                break

            offset += 100
        if download_videos == "1":
            logger.info("Getting video list")
            offset = 0
            while True:
                videos_resp = await self.vk.call(
                    "video.get", owner_id=-self.group_id, count=100, offset=offset
                )
                videos = videos_resp["items"]
                for video in videos:
                    if "player" in video:
                        self.videos_list.append(
                            {
                                "type": video.get("type"),
                                "id": video.get("id"),
                                "owner_id": video.get("owner_id"),
                                "title": video.get("title"),
                                "player": video.get("player"),
                            }
                        )

                if len(videos) < 100:
                    logger.info(f"Total videos received: {len(self.videos_list)}")
                    break

                offset += 100

    def get_single_post(self, post: dict[str, Any]) -> None:
        """
        Process all attachments in a post and select only images.

        This method extracts photo attachments from a single VK post and adds them
        to the photos list for downloading. It filters for photo type attachments
        and extracts the highest resolution URL available.

        Args:
            post: Post dictionary containing attachments array

        Note:
            Only processes attachments of type "photo" and skips other types.
            Uses the highest resolution photo URL available from the sizes array.
            Video processing is commented out due to performance concerns.
        """
        try:
            for i, attachment in enumerate(post["attachments"]):
                if attachment["type"] == "photo":
                    file_type = attachment["type"]
                    photo_id = post["attachments"][i]["photo"]["id"]
                    owner_id = post["attachments"][i]["photo"]["owner_id"]
                    photo_url = post["attachments"][i]["photo"]["sizes"][-1].get("url")
                    if photo_url is not None and photo_url != "":
                        self.photos.append(
                            {
                                "type": file_type,
                                "id": photo_id,
                                "owner_id": -owner_id,
                                "url": photo_url,
                            }
                        )
                """#Too slow
                if attachment["type"] == "video" and download_videos == "1":
                    file_type = attachment["type"]
                    video_id = post["attachments"][i]["video"].get("id")
                    owner_id = post["attachments"][i]["video"].get("owner_id")
                    title = post["attachments"][i]["video"].get("title")
                    photo_title = "{}_{}_{}.mp4".format(owner_id, video_id, title)
                    photo_path = group_dir.joinpath(photo_title)
                    video_link = 'https://vk.com/video_ext.php?oid={}&id={}'.format(owner_id,video_id) #https://vk.com/video_ext.php?oid=-219265779&id=456239543
                    ydl_opts = {'outtmpl': '{}'.format(photo_path), 'quiet': True, 'retries': 10}#, 'progress_hooks': [self.my_hook]}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download(video_link)
                    self.photos.append({
                        "type": file_type,
                        "id": photo_id,
                        "owner_id": owner_id,
                        "url": vid_resp
                    })"""
        except KeyError as e:
            # Missing required fields in post data
            logger.warning(f"Missing required field in post data: {e}")
        except IndexError as e:
            # Invalid attachment structure
            logger.warning(f"Invalid attachment structure: {e}")
        except Exception as e:
            # Any other unexpected error
            logger.error(f"Unexpected error processing post: {e}")

    async def main(self, download_videos_flag: bool = False) -> None:
        """
        Download photos from group wall.

        This method orchestrates the photo downloading process for a single group:
        1. Retrieves group information and creates group directory
        2. Handles closed groups by downloading a placeholder image
        3. For open groups, retrieves all photos and optionally videos from wall posts
        4. Downloads all collected media with progress tracking
        5. Provides detailed logging of the download process

        Args:
            download_videos_flag: Whether to also download videos from the group

        Note:
            Closed groups result in downloading a placeholder community image.
            Photos and videos are downloaded concurrently for better performance.
        """
        # Get group information
        group_info = self.vk.groups.getById(group_id=self.group_id)[0]
        group_name = (
            group_info["name"]
            .replace("/", " ")
            .replace("|", " ")
            .replace(".", " ")
            .strip()
        )

        group_dir = DOWNLOADS_DIR.joinpath(group_name)
        if utils is not None:
            utils.create_dir(group_dir)

        self.photos: list[dict[str, Any]] = []
        self.videos_list: list[dict[str, Any]] = []

        # Group is closed
        if group_info["is_closed"]:
            logger.info(f"Group '{group_name}' is closed :(")
            self.photos = [
                {
                    "id": self.group_id,
                    "owner_id": self.group_id,
                    "url": "https://vk.com/images/community_200.png",
                }
            ]
        else:
            download_vid = "1" if download_videos_flag else "2"
            if download_vid == "1":
                logger.info(f"Getting photos and videos from group '{group_name}'...")
                await self.get_photos(download_vid)
                logger.info(
                    f"Will download {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''}"
                )

                time_start = time.time()

                # Download photos from group wall
                await download_photos(group_dir, self.photos)
                logger.info("Downloading videos")
                await download_videos(group_dir, self.videos_list)

            elif download_vid == "2":
                logger.info(f"Getting photos from group '{group_name}'...")
                await self.get_photos(download_vid)
                logger.info(
                    f"Will download {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''}"
                )

                time_start = time.time()

                # Download photos from group wall
                await download_photos(group_dir, self.photos)
            else:
                logger.info("Invalid value entered")
                time.sleep(0.1)
                return
            # logger.info(f"Getting photos from group '{group_name}'...")

            # Get photos from group wall
            # await self.get_photos(group_dir)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logger.info(
            f"Downloaded {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''} in {download_time} second{'s' if download_time != 1 else ''}"
        )

        # Check for duplicates
        logger.info("Checking for duplicates")
        from ..filter import check_for_duplicates

        dublicates_count = check_for_duplicates(group_dir)
        logger.info(f"Duplicates removed: {dublicates_count}")
        logger.info(
            f"Total downloaded: {len(self.photos) - dublicates_count} photo{'s' if len(self.photos) - dublicates_count != 1 else ''}"
        )


class GroupsPhotoDownloader:
    """Downloader for photos from multiple VK group walls."""

    def __init__(self, group_ids: str, vk_instance: RateLimitedVKAPI) -> None:
        """
        Initialize GroupsPhotoDownloader.

        Args:
            group_ids: Comma-separated string of VK group IDs
            vk_instance: VK API instance
        """
        self.group_ids = [int(id.strip()) for id in group_ids.split(",")]
        self.vk = vk_instance

    async def get_photos(self, group_id: int, download_videos: str) -> None:
        """
        Get photos from a specific group wall.

        Args:
            group_id: VK group ID to get photos from
            download_videos: Whether to download videos ("1" for yes, "2" for no)
        """
        offset = 0
        while True:
            wall_resp = await self.vk.call(
                "wall.get", owner_id=-group_id, count=100, offset=offset
            )
            posts = wall_resp["items"]
            for post in posts:
                # Skip ad posts
                if post["marked_as_ads"]:
                    continue

                # If post is copied from another group
                if "copy_history" in post:
                    if "attachments" in post["copy_history"][0]:
                        self.get_single_post(post["copy_history"][0])

                elif "attachments" in post:
                    self.get_single_post(post)

            if len(posts) < 100:
                break

            offset += 100
        if download_videos == "1":
            logger.info("Getting video list")
            offset = 0
            while True:
                videos_resp = await self.vk.call(
                    "video.get", owner_id=-group_id, count=100, offset=offset
                )
                videos = videos_resp["items"]
                for video in videos:
                    if "player" in video:
                        self.videos_list.append(
                            {
                                "type": video.get("type"),
                                "id": video.get("id"),
                                "owner_id": video.get("owner_id"),
                                "title": video.get("title"),
                                "player": video.get("player"),
                            }
                        )

                if len(videos) < 100:
                    logger.info(f"Total videos received: {len(self.videos_list)}")
                    break

                offset += 100

    def get_single_post(self, post: dict[str, Any]) -> None:
        """
        Process all attachments in a post and select only images.

        Args:
            post: Post dictionary containing attachments
        """
        try:
            for i, attachment in enumerate(post["attachments"]):
                if attachment["type"] == "photo":
                    file_type = attachment["type"]
                    photo_id = post["attachments"][i]["photo"]["id"]
                    owner_id = post["attachments"][i]["photo"]["owner_id"]
                    photo_url = post["attachments"][i]["photo"]["sizes"][-1].get("url")
                    if photo_url is not None and photo_url != "":
                        self.photos.append(
                            {
                                "type": file_type,
                                "id": photo_id,
                                "owner_id": owner_id,
                                "url": photo_url,
                            }
                        )
                """#Too slow
                if attachment["type"] == "video" and download_videos == "1":
                    file_type = attachment["type"]
                    video_id = post["attachments"][i]["video"].get("id")
                    owner_id = post["attachments"][i]["video"].get("owner_id")
                    title = post["attachments"][i]["video"].get("title")
                    photo_title = "{}_{}_{}.mp4".format(owner_id, video_id, title)
                    photo_path = group_dir.joinpath(photo_title)
                    video_link = 'https://vk.com/video_ext.php?oid={}&id={}'.format(owner_id,video_id) #https://vk.com/video_ext.php?oid=-219265779&id=456239543
                    ydl_opts = {'outtmpl': '{}'.format(photo_path), 'quiet': True, 'retries': 10}#, 'progress_hooks': [self.my_hook]}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download(video_link)
                    self.photos.append({
                        "type": file_type,
                        "id": photo_id,
                        "owner_id": owner_id,
                        "url": vid_resp
                    })"""
        except KeyError as e:
            # Missing required fields in post data
            logger.warning(f"Missing required field in post data: {e}")
        except IndexError as e:
            # Invalid attachment structure
            logger.warning(f"Invalid attachment structure: {e}")
        except Exception as e:
            # Any other unexpected error
            logger.error(f"Unexpected error processing post: {e}")

    async def main(self, download_videos_flag: bool = False) -> None:
        """
        Download photos from multiple group walls.

        Args:
            download_videos_flag: Whether to also download videos
        """
        groups_name = ", ".join(
            [await utils.get_group_title(str(group_id)) for group_id in self.group_ids]
            if utils is not None
            else []
        )
        group_dir = DOWNLOADS_DIR.joinpath(groups_name)
        self.photos: list[dict[str, Any]] = []
        self.videos_list: list[dict[str, Any]] = []

        download_vid = "1" if download_videos_flag else "2"

        for group_id in self.group_ids:
            group_info_list = await self.vk.call("groups.getById", group_id=group_id)
            group_info = group_info_list[0]
            # Group is closed
            if group_info["is_closed"]:
                logger.info(f"Group '{groups_name}' is closed :(")
                self.photos = [
                    {
                        "id": group_id,
                        "owner_id": -group_id,
                        "url": "https://vk.com/images/community_200.png",
                    }
                ]
            else:
                if download_vid == "1":
                    logger.info(
                        f"Getting photos and videos from group '{groups_name}'..."
                    )
                    await self.get_photos(group_id, download_vid)
                    logger.info(
                        f"Will download {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''}"
                    )

                    time_start = time.time()

                    # Download photos from group wall
                    await download_photos(group_dir, self.photos)
                    logger.info("Downloading videos")
                    await download_videos(group_dir, self.videos_list)

                elif download_vid == "2":
                    logger.info(f"Getting photos from group '{groups_name}'...")
                    await self.get_photos(group_id, download_vid)
                    logger.info(
                        f"Will download {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''}"
                    )

                    time_start = time.time()

                    # Download photos from group wall
                    await download_photos(group_dir, self.photos)
                else:
                    logger.info("Invalid value entered")
                    time.sleep(0.1)
                    return
                # logger.info(f"Getting photos from group '{group_name}'...")

                # Get photos from group wall
                # await self.get_photos(group_dir)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)

            logger.info(
                f"Downloaded {len(self.photos)} photo{'s' if len(self.photos) != 1 else ''} in {download_time} second{'s' if download_time != 1 else ''}"
            )

            # Check for duplicates
            logger.info("Checking for duplicates")
            from ..filter import check_for_duplicates

            dublicates_count = check_for_duplicates(group_dir)
            logger.info(f"Duplicates removed: {dublicates_count}")
            logger.info(
                f"Total downloaded: {len(self.photos) - dublicates_count} photo{'s' if len(self.photos) - dublicates_count != 1 else ''}"
            )
