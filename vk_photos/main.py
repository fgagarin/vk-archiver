import asyncio
import logging
from pathlib import Path

import click
import vk_api
import yaml
from vk_api.vk_api import VkApiMethod

from .downloaders import (
    ChatMembersPhotoDownloader,
    ChatPhotoDownloader,
    ChatUserPhotoDownloader,
    GroupAlbumsDownloader,
    GroupPhotoDownloader,
    GroupsPhotoDownloader,
    UserPhotoDownloader,
    UsersPhotoDownloader,
)
from .downloaders.chat import set_utils_instance as set_chat_utils_instance
from .downloaders.user import set_utils_instance

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

# Initialize utils instance in downloaders
set_utils_instance(utils)
set_chat_utils_instance(utils)


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
