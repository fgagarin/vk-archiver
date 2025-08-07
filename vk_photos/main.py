import asyncio
import logging
import math
import time
from pathlib import Path

import click
import requests
import vk_api
import yaml
from pytils import numeral
from vk_api.vk_api import VkApiMethod

from .filter import check_for_duplicates
from .functions import decline, download_photos, download_videos, dump

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = Path.cwd().joinpath("downloads")
CONFIG_PATH = BASE_DIR.joinpath("config.yaml")
VK_CONFIG_PATH = BASE_DIR.joinpath("vk_config.v2.json")

with open(CONFIG_PATH, encoding="utf-8") as ymlFile:
    config = yaml.load(ymlFile.read(), Loader=yaml.Loader)

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)

logger = logging.getLogger("vk_api")
logger.disabled = True

loop = asyncio.get_event_loop()


class CLIParameterValidator:
    """Validate CLI parameters for VK Photos downloader."""

    @staticmethod
    def validate_user_id(user_id: str | None) -> str | None:
        """
        Validate user ID parameter.

        Args:
            user_id: User ID to validate

        Returns:
            Validated user ID or None

        Raises:
            click.BadParameter: If user ID is invalid
        """
        if user_id is None:
            return None

        try:
            user_id_int = int(user_id)
            if 1 <= user_id_int <= 2147483647:
                return user_id
        except ValueError:
            pass

        raise click.BadParameter(f"Invalid user ID: {user_id}")

    @staticmethod
    def validate_group_id(group_id: str | None) -> str | None:
        """
        Validate group ID parameter.

        Args:
            group_id: Group ID to validate

        Returns:
            Validated group ID or None

        Raises:
            click.BadParameter: If group ID is invalid
        """
        if group_id is None:
            return None

        try:
            group_id_int = int(group_id)
            if 1 <= group_id_int <= 2147483647:
                return group_id
        except ValueError:
            pass

        raise click.BadParameter(f"Invalid group ID: {group_id}")

    @staticmethod
    def validate_chat_id(chat_id: str | None) -> str | None:
        """
        Validate chat ID parameter.

        Args:
            chat_id: Chat ID to validate

        Returns:
            Validated chat ID or None

        Raises:
            click.BadParameter: If chat ID is invalid
        """
        if chat_id is None:
            return None

        try:
            chat_id_int = int(chat_id)
            if 1 <= chat_id_int <= 2147483647:
                return chat_id
        except ValueError:
            pass

        raise click.BadParameter(f"Invalid chat ID: {chat_id}")

    @staticmethod
    def validate_output_dir(output_dir: str) -> Path:
        """
        Validate and create output directory.

        Args:
            output_dir: Output directory path

        Returns:
            Path object for output directory

        Raises:
            click.BadParameter: If directory cannot be created
        """
        try:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            raise click.BadParameter(f"Cannot create output directory: {e}") from e


class Utils:
    _vk: VkApiMethod | None = None

    def __init__(self):
        """Initialize Utils class and validate configuration."""
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate configuration to ensure only token-based authentication is used.

        Raises:
            RuntimeError: If login/password fields are found in config
        """
        if "login" in config or "password" in config:
            raise RuntimeError(
                "Login/password authentication is forbidden. "
                "Only token-based authentication is allowed. "
                "Remove login and password fields from config.yaml"
            )

    @property
    def vk(self) -> VkApiMethod:
        """Get authenticated VK API instance."""
        if self._vk is None:
            raise RuntimeError(
                "VK API not initialized. Run `auth_by_token` method first."
            )
        return self._vk

    def create_dir(self, dir_path: Path) -> None:
        """
        Create directory if it doesn't exist.

        Args:
            dir_path: Path to the directory to create
        """
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    def auth_by_token(self) -> VkApiMethod:
        """
        Authenticate using VK access token only.

        Returns:
            VkApiMethod: Authenticated VK API instance

        Raises:
            RuntimeError: If token is missing or invalid
        """
        if not config.get("token"):
            logging.error("VK access token is required")
            logging.info("Get token from: https://vkhost.github.io/")
            raise RuntimeError("VK access token is required")

        try:
            vk_session = vk_api.VkApi(token=config["token"])
            self._vk = vk_session.get_api()
            logging.info("Successfully authenticated with token.")
            return self._vk
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            logging.info("Get token from: https://vkhost.github.io/")
            raise RuntimeError("Invalid VK access token") from e

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
            user = self.vk.users.get(user_ids=int(id))
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
            group = self.vk.groups.getById(group_id=int(id))
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
        try:
            # Проверяем, существует ли беседа с таким id
            conversation = self.vk.messages.getConversationsById(
                peer_ids=2000000000 + int(id)
            )
            if conversation["count"] != 0:
                return True
            return False
        except Exception:
            return False

    def get_user_id(self) -> int:
        """
        Get current user ID from VK API.

        Returns:
            Current user ID
        """
        return self.vk.account.getProfileInfo()["id"]

    def get_username(self, user_id: str) -> str:
        """
        Get username by user ID.

        Args:
            user_id: VK user ID

        Returns:
            User's full name
        """
        user = self.vk.users.get(user_id=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"

    def get_group_title(self, group_id: str) -> str:
        """
        Get group title by group ID.

        Args:
            group_id: VK group ID

        Returns:
            Group name with sanitized characters
        """
        group_info = self.vk.groups.getById(group_id=group_id)
        group_name = (
            group_info[0]["name"]
            .replace("/", " ")
            .replace("|", " ")
            .replace(".", " ")
            .strip()
        )
        return group_name

    def get_chat_title(self, chat_id: str) -> str:
        chat_title = self.vk.messages.getConversationsById(
            peer_ids=2000000000 + int(chat_id)
        )["items"][0]["chat_settings"]["title"]
        return chat_title


utils = Utils()


class UserPhotoDownloader:
    def __init__(
        self, user_id: str, vk_instance: VkApiMethod, parent_dir=DOWNLOADS_DIR
    ):
        self.user_id = user_id
        self.vk = vk_instance
        self.parent_dir = parent_dir

    def get_photos(self) -> list[dict]:
        """
        Get all photos from user profile.

        Returns:
            List of photo dictionaries with metadata
        """
        photos = []

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

    async def main(self):
        user_info = self.vk.users.get(
            user_ids=self.user_id, fields="sex, photo_max_orig"
        )[0]

        decline_username = decline(
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            sex=user_info["sex"],
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
    def __init__(self, user_ids: list, vk_instance, parent_dir=DOWNLOADS_DIR):
        self.user_ids = list(user_ids)
        self.vk = vk_instance
        self.parent_dir = parent_dir

    async def main(self):
        for user_id in self.user_ids:
            await UserPhotoDownloader(user_id, self.vk, self.parent_dir).main()


class GroupAlbumsDownloader:
    def __init__(self, group_id: str, vk_instance: VkApiMethod):
        self.group_id = int(group_id)
        self.vk = vk_instance

    async def main(self):
        group_info = self.vk.groups.getById(group_id=self.group_id)[0]
        group_name = (
            group_info["name"]
            .replace("/", " ")
            .replace("|", " ")
            .replace(".", " ")
            .strip()
        )

        group_dir = DOWNLOADS_DIR.joinpath(group_name)
        utils.create_dir(group_dir)
        dump(group_info, group_dir.joinpath("info.yaml"))

        albums = self.vk.photos.getAlbums(owner_id=-self.group_id)["items"]

        for album in albums:
            aid = album["id"]
            album_name = album["title"]
            album_dir = group_dir.joinpath(album_name)
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
    def __init__(self, group_id: str, vk_instance):
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

    def get_single_post(self, post: dict):
        """
        Проходимся по всем вложениям поста и отбираем только картинки
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

    async def main(self, download_videos_flag: bool = False):
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
        dublicates_count = check_for_duplicates(group_dir)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class GroupsPhotoDownloader:
    def __init__(self, group_ids: str, vk_instance):
        self.group_ids = [int(id.strip()) for id in group_ids.split(",")]
        self.vk = vk_instance

    async def get_photos(self, group_id, download_videos):
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

    def get_single_post(self, post: dict):
        """
        Проходимся по всем вложениям поста и отбираем только картинки
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

    async def main(self, download_videos_flag: bool = False):
        """
        Download photos from multiple group walls.

        Args:
            download_videos_flag: Whether to also download videos
        """
        groups_name = ", ".join(
            [utils.get_group_title(group_id) for group_id in self.group_ids]
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
            dublicates_count = check_for_duplicates(group_dir)
            logging.info(f"Дубликатов удалено: {dublicates_count}")

            logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class ChatMembersPhotoDownloader:
    def __init__(self, chat_id: str, vk_instance: VkApiMethod):
        self.chat_id = int(chat_id)
        self.vk = vk_instance

    async def main(self):
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
    def __init__(self, chat_id: str, vk_instance: VkApiMethod):
        self.chat_id = int(chat_id)
        self.vk = vk_instance

    def download_chat_photo(self):
        """
        Скачиваем аватарку беседы если она есть
        """
        if "photo" in self.chat:
            sizes = self.chat["photo"]
            max_size = list(sizes)[-2]
            photo_url = sizes[max_size]
            photo_path = self.chat_dir.joinpath("Аватарка беседы.png")

            response = requests.get(photo_url)
            if response.status_code == 200:
                with open(photo_path, mode="wb") as f:
                    f.write(response.content)

    def get_attachments(self):
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

    async def main(self):
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


# class ChatUserPhotoDownloader:
#     def __init__(self, chat_id: str, vk_instance: VkApiMethod, parent_dir=DOWNLOADS_DIR):
#         self.chat_id = chat_id
#         self.parent_dir = parent_dir
#         self.vk = vk_instance
#     def get_attachments(self):
#         raw_data = self.vk.messages.getHistoryAttachments(
#             peer_id=self.chat_id, media_type="photo"
#         )["items"]

#         photos = []

#         for photo in raw_data:
#             photos.append(
#                 {
#                     "id": photo["attachment"]["photo"]["id"],
#                     "owner_id": photo["attachment"]["photo"]["owner_id"],
#                     "url": photo["attachment"]["photo"]["sizes"][-1]["url"],
#                 }
#             )

#         return photos

#     async def main(self):
#         username = utils.get_username(self.chat_id)

#         photos_path = self.parent_dir.joinpath(f"Переписка {username}")
#         utils.create_dir(photos_path)

#         photos = self.get_attachments()

#         logging.info(
#             "{} {} {}".format(
#                 numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
#                 numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
#                 numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
#             )
#         )

#         time_start = time.time()

#         await download_photos(photos_path, photos)

#         time_finish = time.time()
#         download_time = math.ceil(time_finish - time_start)

#         logging.info(
#             "{} {} за {}".format(
#                 numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
#                 numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
#                 numeral.get_plural(download_time, "секунду, секунды, секунд"),
#             )
#         )

#         logging.info("Проверка на дубликаты")
#         dublicates_count = check_for_duplicates(photos_path)
#         logging.info(f"Дубликатов удалено: {dublicates_count}")

#         logging.info(f"Итого скачено: {len(photos) - dublicates_count} фото")


class ChatUserPhotoDownloader:
    def __init__(
        self, chat_id: str, vk_instance: VkApiMethod, parent_dir=DOWNLOADS_DIR
    ):
        self.chat_id = chat_id
        self.parent_dir = parent_dir
        self.vk = vk_instance

    def get_attachments(self):
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

    async def main(self):
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


@click.group()
@click.option(
    "--output-dir",
    "-o",
    default="./downloads",
    envvar="VK_OUTPUT_DIR",
    help="Output directory for downloaded photos",
)
@click.option(
    "--download-videos",
    "-v",
    is_flag=True,
    envvar="VK_DOWNLOAD_VIDEOS",
    help="Also download videos",
)
@click.option(
    "--rate-limit",
    "-r",
    default=3,
    type=int,
    envvar="VK_RATE_LIMIT",
    help="API requests per second",
)
@click.pass_context
def main(
    ctx: click.Context, output_dir: str, download_videos: bool, rate_limit: int
) -> None:
    """
    VK.com Photo Scrobler - Download photos from VK profiles, groups, and chats.

    This tool allows you to download photos from various VK sources including
    user profiles, group walls, chat conversations, and chat member profiles.

    Authentication is done via VK access token stored in config.yaml or VK_TOKEN environment variable.
    """
    # Ensure context object is created
    ctx.ensure_object(dict)

    # Store options in context
    ctx.obj["output_dir"] = CLIParameterValidator.validate_output_dir(output_dir)
    ctx.obj["download_videos"] = download_videos
    ctx.obj["rate_limit"] = rate_limit

    # Create downloads directory
    utils.create_dir(ctx.obj["output_dir"])


@main.command()
@click.option(
    "--user-id",
    "-u",
    required=True,
    envvar="VK_USER_ID",
    help="VK user ID to download photos from",
)
@click.pass_context
def user(ctx: click.Context, user_id: str) -> None:
    """Download all photos from a single user profile."""
    validated_user_id = CLIParameterValidator.validate_user_id(user_id)
    if validated_user_id is None:
        raise click.BadParameter("User ID is required")

    if not utils.check_user_id(validated_user_id):
        raise click.BadParameter(f"User with ID {validated_user_id} does not exist")

    vk = utils.auth_by_token()
    downloader = UserPhotoDownloader(
        user_id=validated_user_id, vk_instance=vk, parent_dir=ctx.obj["output_dir"]
    )
    loop.run_until_complete(downloader.main())


@main.command()
@click.option(
    "--user-ids",
    "-u",
    required=True,
    envvar="VK_USER_IDS",
    help="Comma-separated list of VK user IDs",
)
@click.pass_context
def users(ctx: click.Context, user_ids: str) -> None:
    """Download all photos from multiple user profiles."""
    user_id_list = [uid.strip() for uid in user_ids.split(",")]

    # Validate each user ID
    for user_id in user_id_list:
        CLIParameterValidator.validate_user_id(user_id)
        if not utils.check_user_id(user_id):
            raise click.BadParameter(f"User with ID {user_id} does not exist")

    vk = utils.auth_by_token()
    downloader = UsersPhotoDownloader(
        user_ids=user_id_list, vk_instance=vk, parent_dir=ctx.obj["output_dir"]
    )
    loop.run_until_complete(downloader.main())


@main.command()
@click.option(
    "--group-id",
    "-g",
    required=True,
    envvar="VK_GROUP_ID",
    help="VK group ID to download photos from",
)
@click.pass_context
def group(ctx: click.Context, group_id: str) -> None:
    """Download all photos from a single group wall."""
    validated_group_id = CLIParameterValidator.validate_group_id(group_id)
    if validated_group_id is None:
        raise click.BadParameter("Group ID is required")

    if not utils.check_group_id(validated_group_id):
        raise click.BadParameter(f"Group with ID {validated_group_id} does not exist")

    vk = utils.auth_by_token()
    downloader = GroupPhotoDownloader(group_id=validated_group_id, vk_instance=vk)
    loop.run_until_complete(downloader.main(ctx.obj["download_videos"]))


@main.command()
@click.option(
    "--group-ids",
    "-g",
    required=True,
    envvar="VK_GROUP_IDS",
    help="Comma-separated list of VK group IDs",
)
@click.pass_context
def groups(ctx: click.Context, group_ids: str) -> None:
    """Download all photos from multiple group walls."""
    group_id_list = [gid.strip() for gid in group_ids.split(",")]

    # Validate each group ID
    for group_id in group_id_list:
        CLIParameterValidator.validate_group_id(group_id)
        if not utils.check_group_id(group_id):
            raise click.BadParameter(f"Group with ID {group_id} does not exist")

    vk = utils.auth_by_token()
    downloader = GroupsPhotoDownloader(
        group_ids=",".join(group_id_list), vk_instance=vk
    )
    loop.run_until_complete(downloader.main(ctx.obj["download_videos"]))


@main.command()
@click.option(
    "--chat-id",
    "-c",
    required=True,
    envvar="VK_CHAT_ID",
    help="VK chat ID to download member photos from",
)
@click.pass_context
def chat_members(ctx: click.Context, chat_id: str) -> None:
    """Download all photos from chat members."""
    validated_chat_id = CLIParameterValidator.validate_chat_id(chat_id)
    if validated_chat_id is None:
        raise click.BadParameter("Chat ID is required")

    if not utils.check_chat_id(validated_chat_id):
        raise click.BadParameter(f"Chat with ID {validated_chat_id} does not exist")

    vk = utils.auth_by_token()
    downloader = ChatMembersPhotoDownloader(chat_id=validated_chat_id, vk_instance=vk)
    loop.run_until_complete(downloader.main())


@main.command()
@click.option(
    "--chat-id",
    "-c",
    required=True,
    envvar="VK_CHAT_ID",
    help="VK chat ID to download attachments from",
)
@click.pass_context
def chat_attachments(ctx: click.Context, chat_id: str) -> None:
    """Download all attachments from a chat conversation."""
    validated_chat_id = CLIParameterValidator.validate_chat_id(chat_id)
    if validated_chat_id is None:
        raise click.BadParameter("Chat ID is required")

    if not utils.check_chat_id(validated_chat_id):
        raise click.BadParameter(f"Chat with ID {validated_chat_id} does not exist")

    vk = utils.auth_by_token()
    downloader = ChatPhotoDownloader(chat_id=validated_chat_id, vk_instance=vk)
    loop.run_until_complete(downloader.main())


@main.command()
@click.option(
    "--user-id",
    "-u",
    required=True,
    envvar="VK_USER_ID",
    help="VK user ID to download chat photos from",
)
@click.pass_context
def user_chat(ctx: click.Context, user_id: str) -> None:
    """Download all photos from a user's chat conversation."""
    validated_user_id = CLIParameterValidator.validate_user_id(user_id)
    if validated_user_id is None:
        raise click.BadParameter("User ID is required")

    if not utils.check_user_id(validated_user_id):
        raise click.BadParameter(f"User with ID {validated_user_id} does not exist")

    vk = utils.auth_by_token()
    downloader = ChatUserPhotoDownloader(
        chat_id=validated_user_id, vk_instance=vk, parent_dir=ctx.obj["output_dir"]
    )
    loop.run_until_complete(downloader.main())


@main.command()
@click.option(
    "--group-id",
    "-g",
    required=True,
    envvar="VK_GROUP_ID",
    help="VK group ID to download albums from",
)
@click.pass_context
def group_albums(ctx: click.Context, group_id: str) -> None:
    """Download all photos from group albums."""
    validated_group_id = CLIParameterValidator.validate_group_id(group_id)
    if validated_group_id is None:
        raise click.BadParameter("Group ID is required")

    if not utils.check_group_id(validated_group_id):
        raise click.BadParameter(f"Group with ID {validated_group_id} does not exist")

    vk = utils.auth_by_token()
    downloader = GroupAlbumsDownloader(group_id=validated_group_id, vk_instance=vk)
    loop.run_until_complete(downloader.main())


if __name__ == "__main__":
    main()
