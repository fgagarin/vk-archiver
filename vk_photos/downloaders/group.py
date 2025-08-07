"""Group photo downloader classes for VK Photos application."""

import logging
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pytils import numeral
from vk_api.vk_api import VkApiMethod

from ..functions import download_photos, download_videos, dump

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


class GroupAlbumsDownloader:
    """Downloader for albums from a VK group."""

    def __init__(self, group_id: str, vk_instance: VkApiMethod) -> None:
        """
        Initialize GroupAlbumsDownloader.

        Args:
            group_id: VK group ID to download albums from
            vk_instance: VK API instance
        """
        self.group_id = int(group_id)
        self.vk = vk_instance

    async def main(self) -> None:
        """Download all albums from the group."""
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
        dump(group_info, group_dir.joinpath("info.yaml"))

        albums = self.vk.photos.getAlbums(owner_id=-self.group_id)["items"]

        for album in albums:
            aid = album["id"]
            album_name = album["title"]
            album_dir = group_dir.joinpath(album_name)
            if utils is not None:
                utils.create_dir(album_dir)
            dump(album, album_dir.joinpath("info.yaml"))

            photos = []
            offset = 0
            while True:
                album_photos = self.vk.photos.get(
                    owner_id=-self.group_id,
                    album_id=aid,
                    count=100,
                    offset=offset,
                    photo_sizes=True,
                    extended=True,
                )["items"]

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

    def __init__(self, group_id: str, vk_instance: VkApiMethod) -> None:
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

        Args:
            download_videos: Whether to download videos ("1" for yes, "2" for no)
        """
        offset = 0
        while True:
            posts = self.vk.wall.get(owner_id=-self.group_id, count=100, offset=offset)[
                "items"
            ]
            for post in posts:
                # Пропускаем посты с рекламой
                if post["marked_as_ads"]:
                    continue

                # Если пост скопирован с другой группы
                if "copy_history" in post:
                    if "attachments" in post["copy_history"][0]:
                        self.get_single_post(post["copy_history"][0])

                elif "attachments" in post:
                    self.get_single_post(post)

            if len(posts) < 100:
                break

            offset += 100
        if download_videos == "1":
            logging.info("Получаем список видео")
            offset = 0
            while True:
                videos = self.vk.video.get(
                    owner_id=-self.group_id, count=100, offset=offset
                )["items"]
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
                    logging.info(f"Всего получено {len(self.videos_list)} видео")
                    break

                offset += 100

    def get_single_post(self, post: dict) -> None:
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
                    print(photo_title)
                    ydl_opts = {'outtmpl': '{}'.format(photo_path), 'quiet': True, 'retries': 10}#, 'progress_hooks': [self.my_hook]}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download(video_link)
                    self.photos.append({
                        "type": file_type,
                        "id": photo_id,
                        "owner_id": owner_id,
                        "url": vid_resp
                    })"""
        except Exception as e:
            print(e)

    async def main(self, download_videos_flag: bool = False) -> None:
        """
        Download photos from group wall.

        Args:
            download_videos_flag: Whether to also download videos
        """
        # Получаем информацию о группе
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

        self.photos = []
        self.videos_list = []

        # Группа закрыта
        if group_info["is_closed"]:
            logging.info(f"Группа '{group_name}' закрыта :(")
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
                logging.info(f"Получаем фотографии и видео группы '{group_name}'...")
                await self.get_photos(download_vid)
                logging.info(
                    "{} {} {}".format(
                        numeral.choose_plural(len(self.photos), "Будет, Будут, Будут"),
                        numeral.choose_plural(
                            len(self.photos), "скачена, скачены, скачены"
                        ),
                        numeral.get_plural(
                            len(self.photos), "фотография, фотографии, фотографий"
                        ),
                    )
                )

                time_start = time.time()

                # Скачиваем фотографии со стены группы
                await download_photos(group_dir, self.photos)
                logging.info("Скачиваем видео")
                await download_videos(group_dir, self.videos_list)

            elif download_vid == "2":
                logging.info(f"Получаем фотографии группы '{group_name}'...")
                await self.get_photos(download_vid)
                logging.info(
                    "{} {} {}".format(
                        numeral.choose_plural(len(self.photos), "Будет, Будут, Будут"),
                        numeral.choose_plural(
                            len(self.photos), "скачена, скачены, скачены"
                        ),
                        numeral.get_plural(
                            len(self.photos), "фотография, фотографии, фотографий"
                        ),
                    )
                )

                time_start = time.time()

                # Скачиваем фотографии со стены группы
                await download_photos(group_dir, self.photos)
            else:
                logging.info("Введено некорректное значение")
                time.sleep(0.1)
                exit()
            # logging.info(f"Получаем фотографии группы '{group_name}'...")

            # Получаем фотографии со стены группы
            # await self.get_photos(group_dir)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info(
            "{} {} за {}".format(
                numeral.choose_plural(len(self.photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(
                    len(self.photos), "фотография, фотографии, фотографий"
                ),
                numeral.get_plural(download_time, "секунду, секунды, секунд"),
            )
        )

        logging.info("Проверка на дубликаты")
        from ..filter import check_for_duplicates

        dublicates_count = check_for_duplicates(group_dir)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class GroupsPhotoDownloader:
    """Downloader for photos from multiple VK group walls."""

    def __init__(self, group_ids: str, vk_instance: VkApiMethod) -> None:
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
            posts = self.vk.wall.get(owner_id=-group_id, count=100, offset=offset)[
                "items"
            ]
            for post in posts:
                # Пропускаем посты с рекламой
                if post["marked_as_ads"]:
                    continue

                # Если пост скопирован с другой группы
                if "copy_history" in post:
                    if "attachments" in post["copy_history"][0]:
                        self.get_single_post(post["copy_history"][0])

                elif "attachments" in post:
                    self.get_single_post(post)

            if len(posts) < 100:
                break

            offset += 100
        if download_videos == "1":
            logging.info("Получаем список видео")
            offset = 0
            while True:
                videos = self.vk.video.get(
                    owner_id=-group_id, count=100, offset=offset
                )["items"]
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
                    logging.info(f"Всего получено {len(self.videos_list)} видео")
                    break

                offset += 100

    def get_single_post(self, post: dict) -> None:
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
                    print(photo_title)
                    ydl_opts = {'outtmpl': '{}'.format(photo_path), 'quiet': True, 'retries': 10}#, 'progress_hooks': [self.my_hook]}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download(video_link)
                    self.photos.append({
                        "type": file_type,
                        "id": photo_id,
                        "owner_id": owner_id,
                        "url": vid_resp
                    })"""
        except Exception as e:
            print(e)

    async def main(self, download_videos_flag: bool = False) -> None:
        """
        Download photos from multiple group walls.

        Args:
            download_videos_flag: Whether to also download videos
        """
        groups_name = ", ".join(
            [utils.get_group_title(str(group_id)) for group_id in self.group_ids]
            if utils is not None
            else []
        )
        group_dir = DOWNLOADS_DIR.joinpath(groups_name)
        self.photos = []
        self.videos_list = []

        download_vid = "1" if download_videos_flag else "2"

        for group_id in self.group_ids:
            group_info = self.vk.groups.getById(group_id=group_id)[0]
            # Группа закрыта
            if group_info["is_closed"]:
                logging.info(f"Группа '{groups_name}' закрыта :(")
                self.photos = [
                    {
                        "id": group_id,
                        "owner_id": -group_id,
                        "url": "https://vk.com/images/community_200.png",
                    }
                ]
            else:
                if download_vid == "1":
                    logging.info(
                        f"Получаем фотографии и видео группы '{groups_name}'..."
                    )
                    await self.get_photos(group_id, download_vid)
                    logging.info(
                        "{} {} {}".format(
                            numeral.choose_plural(
                                len(self.photos), "Будет, Будут, Будут"
                            ),
                            numeral.choose_plural(
                                len(self.photos), "скачена, скачены, скачены"
                            ),
                            numeral.get_plural(
                                len(self.photos), "фотография, фотографии, фотографий"
                            ),
                        )
                    )

                    time_start = time.time()

                    # Скачиваем фотографии со стены группы
                    await download_photos(group_dir, self.photos)
                    logging.info("Скачиваем видео")
                    await download_videos(group_dir, self.videos_list)

                elif download_vid == "2":
                    logging.info(f"Получаем фотографии группы '{groups_name}'...")
                    await self.get_photos(group_id, download_vid)
                    logging.info(
                        "{} {} {}".format(
                            numeral.choose_plural(
                                len(self.photos), "Будет, Будут, Будут"
                            ),
                            numeral.choose_plural(
                                len(self.photos), "скачена, скачены, скачены"
                            ),
                            numeral.get_plural(
                                len(self.photos), "фотография, фотографии, фотографий"
                            ),
                        )
                    )

                    time_start = time.time()

                    # Скачиваем фотографии со стены группы
                    await download_photos(group_dir, self.photos)
                else:
                    logging.info("Введено некорректное значение")
                    time.sleep(0.1)
                    return
                # logging.info(f"Получаем фотографии группы '{group_name}'...")

                # Получаем фотографии со стены группы
                # await self.get_photos(group_dir)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)

            logging.info(
                "{} {} за {}".format(
                    numeral.choose_plural(
                        len(self.photos), "Скачена, Скачены, Скачены"
                    ),
                    numeral.get_plural(
                        len(self.photos), "фотография, фотографии, фотографий"
                    ),
                    numeral.get_plural(download_time, "секунду, секунды, секунд"),
                )
            )

            logging.info("Проверка на дубликаты")
            from ..filter import check_for_duplicates

            dublicates_count = check_for_duplicates(group_dir)
            logging.info(f"Дубликатов удалено: {dublicates_count}")

            logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")
