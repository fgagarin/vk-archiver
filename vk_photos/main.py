import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click
from dotenv import load_dotenv

from .downloaders import (
    ChatMembersPhotoDownloader,
    ChatPhotoDownloader,
    ChatUserPhotoDownloader,
    GroupAlbumsDownloader,
    GroupPhotoDownloader,
    GroupsPhotoDownloader,
    MetadataDownloader,
    PhotosDownloader,
    UserPhotoDownloader,
    UsersPhotoDownloader,
    VideosDownloader,
    WallDownloader,
)
from .utils import Utils
from .utils.exceptions import (
    APIError,
    PermissionError,
    ResourceNotFoundError,
    ValidationError,
)
from .utils.logging_config import setup_logging

if TYPE_CHECKING:
    from .utils import Utils

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = Path.cwd().joinpath("downloads")
CONFIG_PATH = BASE_DIR.joinpath("config.yaml")
VK_CONFIG_PATH = BASE_DIR.joinpath("vk_config.v2.json")

# Load environment variables from .env before anything else uses envvars
load_dotenv()

# Set up centralized logging
logger = setup_logging(level=logging.INFO)

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
        except PermissionError as e:
            raise click.BadParameter(
                f"Cannot create output directory due to permission error: {e}"
            ) from e
        except OSError as e:
            raise click.BadParameter(
                f"Cannot create output directory due to system error: {e}"
            ) from e
        except Exception as e:
            raise click.BadParameter(f"Cannot create output directory: {e}") from e


# Global utils instance - will be initialized with rate limit in main function
utils: Utils | None = None


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
    global utils

    # Ensure context object is created
    ctx.ensure_object(dict)

    # Store options in context
    ctx.obj["output_dir"] = CLIParameterValidator.validate_output_dir(output_dir)
    ctx.obj["download_videos"] = download_videos
    ctx.obj["rate_limit"] = rate_limit

    # Initialize utils instance with rate limit
    utils = Utils(CONFIG_PATH, rate_limit)

    # Create downloads directory
    utils.create_dir(ctx.obj["output_dir"])


@main.command()
@click.option(
    "--group",
    required=True,
    help=(
        "Group screen name or numeric id (without minus). "
        "Resolves to canonical folder name and group id."
    ),
)
@click.option(
    "--types",
    default="all",
    help=(
        "Comma-separated list of types to download: metadata,wall,photos,videos,documents,stories. "
        "Use 'all' to download everything."
    ),
)
@click.option(
    "--output",
    default="downloads",
    show_default=True,
    help="Base output directory",
)
@click.option(
    "--since", default=None, help="Only include items on/after this date (YYYY-MM-DD)"
)
@click.option(
    "--until", default=None, help="Only include items on/before this date (YYYY-MM-DD)"
)
@click.option(
    "--max-items",
    type=int,
    default=None,
    help="Per-type cap. If omitted, download everything",
)
@click.option(
    "--concurrency",
    type=int,
    default=8,
    show_default=True,
    help="Number of parallel API fetches/downloads",
)
@click.option(
    "--resume/--no-resume",
    default=True,
    show_default=True,
    help="Resume from saved cursors/offsets if present",
)
@click.option("--api-version", default=None, help="Override VK API version")
@click.option("--dry-run", is_flag=True, help="Print plan only; no network or writes")
@click.pass_context
def download(
    ctx: click.Context,
    group: str,
    types: str,
    output: str,
    since: str | None,
    until: str | None,
    max_items: int | None,
    concurrency: int,
    resume: bool,
    api_version: str | None,
    dry_run: bool,
) -> None:
    """
    Download content from a VK community by types.

    Step 1 bootstrapping: only resolves group and prints the execution plan. Actual
    per-type downloaders will be wired in subsequent steps.
    """
    if utils is None:
        raise click.BadParameter(
            "Utils not initialized. Please run the main command first."
        )

    utils_instance = utils

    # Ensure VK API is authenticated for resolution/API probes
    utils_instance.auth_by_token()

    # Resolve group to canonical info
    resolved = loop.run_until_complete(utils_instance.resolve_group(group))

    # Derive final base directory using canonical folder name
    base_dir = Path(output).joinpath(resolved.folder_name)

    plan = {
        "group_id": resolved.id,
        "screen_name": resolved.screen_name,
        "group_title": resolved.name,
        "folder": str(base_dir),
        "types": "all"
        if types.strip().lower() == "all"
        else [t.strip() for t in types.split(",") if t.strip()],
        "since": since,
        "until": until,
        "max_items": max_items,
        "concurrency": concurrency,
        "resume": resume,
        "api_version": api_version,
        "dry_run": dry_run,
    }

    # For step 3: if metadata type is requested (or all), fetch and persist it
    selected_types = plan["types"]
    if selected_types == "all" or "metadata" in selected_types:
        from .downloaders.metadata import MetadataRunConfig

        run_cfg = MetadataRunConfig(
            group_id=resolved.id,
            screen_name=resolved.screen_name,
            types=selected_types,
            output_dir=str(output),
            since=since,
            until=until,
            max_items=max_items,
            concurrency=concurrency,
            resume=resume,
            api_version=api_version,
        )

        if dry_run:
            click.echo(
                "[dry-run] Would download community metadata and write meta files"
            )
        else:
            downloader = MetadataDownloader(
                vk=utils_instance.vk,
                utils=utils_instance,
                base_dir=base_dir,
                group_id=resolved.id,
                screen_name=resolved.screen_name,
                run_config=run_cfg,
            )
            loop.run_until_complete(downloader.run())

    # Always print the execution plan at the end for visibility
    click.echo("Download plan:")
    for key, value in plan.items():
        click.echo(f"  - {key}: {value}")

    # Wall content after metadata (if requested)
    if selected_types == "all" or "wall" in selected_types:
        if dry_run:
            click.echo("[dry-run] Would download wall posts and attachments index")
        else:
            wall = WallDownloader(
                vk=utils_instance.vk,
                utils=utils_instance,
                base_dir=base_dir,
                group_id=resolved.id,
                since=since,
                until=until,
                max_items=max_items,
            )
            loop.run_until_complete(wall.run())

    # Photos (albums and photos) after wall
    if selected_types == "all" or "photos" in selected_types:
        if dry_run:
            click.echo("[dry-run] Would download albums and photos into albums folders")
        else:
            photos = PhotosDownloader(
                vk=utils_instance.vk,
                utils=utils_instance,
                base_dir=base_dir,
                group_id=resolved.id,
                max_items=max_items,
            )
            loop.run_until_complete(photos.run())

    # Videos after photos
    if selected_types == "all" or "videos" in selected_types:
        if dry_run:
            click.echo(
                "[dry-run] Would download videos metadata and files when allowed"
            )
        else:
            videos = VideosDownloader(
                vk=utils_instance.vk,
                utils=utils_instance,
                base_dir=base_dir,
                group_id=resolved.id,
                max_items=max_items,
            )
            loop.run_until_complete(videos.run())


@click.option(
    "--user-id",
    "-u",
    required=True,
    envvar="VK_USER_ID",
    help="VK user ID to download photos from",
)
@click.pass_context
def user(ctx: click.Context, user_id: str) -> None:
    """
    Download all photos from a single user profile.

    This command downloads photos from a VK user's profile, including saved photos,
    profile photos, wall photos, and all photos. The photos are organized by user
    name in the output directory.

    Args:
        ctx: Click context containing output directory and other options
        user_id: VK user ID to download photos from

    Raises:
        click.BadParameter: If user ID is invalid or user doesn't exist
    """
    if utils is None:
        raise click.BadParameter(
            "Utils not initialized. Please run the main command first."
        )

    # Type assertion after None check
    utils_instance = utils

    validated_user_id = CLIParameterValidator.validate_user_id(user_id)
    if validated_user_id is None:
        raise click.BadParameter("User ID is required")

    try:
        loop.run_until_complete(
            utils_instance.validator.validate_user_id(validated_user_id)
        )
    except ValidationError as e:
        raise click.BadParameter(f"Invalid user ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"User with ID {validated_user_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate user: {e}") from e

    vk = utils_instance.auth_by_token()
    downloader = UserPhotoDownloader(
        user_id=validated_user_id,
        vk_instance=vk,
        utils=utils_instance,
        parent_dir=ctx.obj["output_dir"],
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
    """
    Download all photos from multiple user profiles.

    This command downloads photos from multiple VK user profiles. Each user's photos
    are downloaded sequentially and organized in separate directories by user name.

    Args:
        ctx: Click context containing output directory and other options
        user_ids: Comma-separated list of VK user IDs to download photos from

    Raises:
        click.BadParameter: If any user ID is invalid or user doesn't exist
    """
    user_id_list = [uid.strip() for uid in user_ids.split(",")]

    # Validate each user ID
    for user_id in user_id_list:
        CLIParameterValidator.validate_user_id(user_id)
        try:
            utils.validator.validate_user_id(user_id)
        except ValidationError as e:
            raise click.BadParameter(f"Invalid user ID: {e}") from e
        except ResourceNotFoundError as e:
            raise click.BadParameter(f"User with ID {user_id} does not exist") from e
        except APIError as e:
            raise click.BadParameter(f"Failed to validate user: {e}") from e

    vk = utils.auth_by_token()
    downloader = UsersPhotoDownloader(
        user_ids=user_id_list,
        vk_instance=vk,
        utils=utils,
        parent_dir=ctx.obj["output_dir"],
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
    """
    Download all photos from a single group wall.

    This command downloads photos from a VK group's wall posts. It processes all
    posts in the group and extracts photos and optionally videos from each post.
    Photos are organized by group name in the output directory.

    Args:
        ctx: Click context containing output directory, download_videos, and other options
        group_id: VK group ID to download photos from

    Raises:
        click.BadParameter: If group ID is invalid or group doesn't exist
    """
    validated_group_id = CLIParameterValidator.validate_group_id(group_id)
    if validated_group_id is None:
        raise click.BadParameter("Group ID is required")

    try:
        utils.validator.validate_group_id(validated_group_id)
    except ValidationError as e:
        raise click.BadParameter(f"Invalid group ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"Group with ID {validated_group_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate group: {e}") from e

    vk = utils.auth_by_token()
    downloader = GroupPhotoDownloader(
        group_id=validated_group_id, vk_instance=vk, utils=utils
    )
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
    """
    Download all photos from multiple group walls.

    This command downloads photos from multiple VK group walls. Each group's photos
    are downloaded sequentially and organized in separate directories by group name.
    Videos can also be downloaded if the --download-videos flag is set.

    Args:
        ctx: Click context containing output directory, download_videos, and other options
        group_ids: Comma-separated list of VK group IDs to download photos from

    Raises:
        click.BadParameter: If any group ID is invalid or group doesn't exist
    """
    group_id_list = [gid.strip() for gid in group_ids.split(",")]

    # Validate each group ID
    for group_id in group_id_list:
        CLIParameterValidator.validate_group_id(group_id)
        try:
            utils.validator.validate_group_id(group_id)
        except ValidationError as e:
            raise click.BadParameter(f"Invalid group ID: {e}") from e
        except ResourceNotFoundError as e:
            raise click.BadParameter(f"Group with ID {group_id} does not exist") from e
        except APIError as e:
            raise click.BadParameter(f"Failed to validate group: {e}") from e

    vk = utils.auth_by_token()
    downloader = GroupsPhotoDownloader(
        group_ids=",".join(group_id_list), vk_instance=vk, utils=utils
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
    """
    Download all photos from chat members.

    This command downloads photos from all members of a VK chat conversation.
    It retrieves the list of chat members and downloads their profile photos
    and other photos from their profiles. Photos are organized by chat name.

    Args:
        ctx: Click context containing output directory and other options
        chat_id: VK chat ID to download member photos from

    Raises:
        click.BadParameter: If chat ID is invalid or chat doesn't exist
    """
    validated_chat_id = CLIParameterValidator.validate_chat_id(chat_id)
    if validated_chat_id is None:
        raise click.BadParameter("Chat ID is required")

    try:
        utils.validator.validate_chat_id(validated_chat_id)
    except ValidationError as e:
        raise click.BadParameter(f"Invalid chat ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"Chat with ID {validated_chat_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate chat: {e}") from e

    vk = utils.auth_by_token()
    downloader = ChatMembersPhotoDownloader(
        chat_id=validated_chat_id, vk_instance=vk, utils=utils
    )
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
    """
    Download all attachments from a chat conversation.

    This command downloads all photo attachments from a VK chat conversation.
    It retrieves the chat history and extracts all photo attachments from
    messages. Photos are organized by chat name in the output directory.

    Args:
        ctx: Click context containing output directory and other options
        chat_id: VK chat ID to download attachments from

    Raises:
        click.BadParameter: If chat ID is invalid or chat doesn't exist
    """
    validated_chat_id = CLIParameterValidator.validate_chat_id(chat_id)
    if validated_chat_id is None:
        raise click.BadParameter("Chat ID is required")

    try:
        utils.validator.validate_chat_id(validated_chat_id)
    except ValidationError as e:
        raise click.BadParameter(f"Invalid chat ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"Chat with ID {validated_chat_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate chat: {e}") from e

    vk = utils.auth_by_token()
    downloader = ChatPhotoDownloader(
        chat_id=validated_chat_id, vk_instance=vk, utils=utils
    )
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
    """
    Download all photos from a user's chat conversation.

    This command downloads all photo attachments from a private chat conversation
    with a specific VK user. It retrieves the chat history and extracts all
    photo attachments from messages. Photos are organized by user name.

    Args:
        ctx: Click context containing output directory and other options
        user_id: VK user ID to download chat photos from

    Raises:
        click.BadParameter: If user ID is invalid or user doesn't exist
    """
    validated_user_id = CLIParameterValidator.validate_user_id(user_id)
    if validated_user_id is None:
        raise click.BadParameter("User ID is required")

    try:
        utils.validator.validate_user_id(validated_user_id)
    except ValidationError as e:
        raise click.BadParameter(f"Invalid user ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"User with ID {validated_user_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate user: {e}") from e

    vk = utils.auth_by_token()
    downloader = ChatUserPhotoDownloader(
        chat_id=validated_user_id,
        vk_instance=vk,
        utils=utils,
        parent_dir=ctx.obj["output_dir"],
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
    """
    Download all photos from group albums.

    This command downloads all photos from all albums of a VK group. It retrieves
    the list of albums and downloads all photos from each album. Photos are
    organized by group name and album name in the output directory.

    Args:
        ctx: Click context containing output directory and other options
        group_id: VK group ID to download albums from

    Raises:
        click.BadParameter: If group ID is invalid or group doesn't exist
    """
    validated_group_id = CLIParameterValidator.validate_group_id(group_id)
    if validated_group_id is None:
        raise click.BadParameter("Group ID is required")

    try:
        utils.validator.validate_group_id(validated_group_id)
    except ValidationError as e:
        raise click.BadParameter(f"Invalid group ID: {e}") from e
    except ResourceNotFoundError as e:
        raise click.BadParameter(
            f"Group with ID {validated_group_id} does not exist"
        ) from e
    except APIError as e:
        raise click.BadParameter(f"Failed to validate group: {e}") from e

    vk = utils.auth_by_token()
    downloader = GroupAlbumsDownloader(
        group_id=validated_group_id, vk_instance=vk, utils=utils
    )
    loop.run_until_complete(downloader.main())


if __name__ == "__main__":
    main()
