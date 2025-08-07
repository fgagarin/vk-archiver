import asyncio
import json
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp
import yaml
import yt_dlp
from pytrovich.enums import Case, Gender, NamePart
from pytrovich.maker import PetrovichDeclinationMaker
from tqdm.asyncio import tqdm

maker = PetrovichDeclinationMaker()


def decline(first_name: str, last_name: str, sex: int) -> str:
    """
    Return first name and last name in genitive case.

    Args:
        first_name: First name to decline
        last_name: Last name to decline
        sex: Gender (1 for female, 2 for male)

    Returns:
        Declined first name and last name as a string
    """
    if sex == 1:
        first_name = maker.make(
            NamePart.FIRSTNAME, Gender.FEMALE, Case.GENITIVE, first_name
        )
        last_name = maker.make(
            NamePart.LASTNAME, Gender.FEMALE, Case.GENITIVE, last_name
        )
    elif sex == 2:
        first_name = maker.make(
            NamePart.FIRSTNAME, Gender.MALE, Case.GENITIVE, first_name
        )
        last_name = maker.make(NamePart.LASTNAME, Gender.MALE, Case.GENITIVE, last_name)
    return f"{first_name} {last_name}"


def write_json(data: Any, title: str = "data") -> None:
    """
    Write data to a JSON file.

    Args:
        data: Data to write to JSON file
        title: Base name for the JSON file (without extension)
    """
    with open(title + ".json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def dump(data: Any, file_path: Path) -> None:
    """
    Write data to a YAML file.

    Args:
        data: Data to write to YAML file
        file_path: Path to the YAML file
    """
    with open(file_path, "w", encoding="utf-8") as file:
        yaml.dump(data, file, indent=2, allow_unicode=True)


async def download_photo(
    session: aiohttp.ClientSession, photo_url: str, photo_path: Path
) -> None:
    """
    Download a single photo from URL to local path.

    Args:
        session: aiohttp client session for making HTTP requests
        photo_url: URL of the photo to download
        photo_path: Local path where to save the photo
    """
    try:
        if not photo_path.exists():
            async with session.get(photo_url) as response:
                if response.status == 200:
                    async with aiofiles.open(photo_path, "wb") as f:
                        await f.write(await response.read())
    except Exception as e:
        print(e)


async def download_photos(photos_path: Path, photos: list[dict[str, Any]]) -> None:
    """
    Download multiple photos concurrently.

    Args:
        photos_path: Directory path where to save photos
        photos: List of photo dictionaries containing 'owner_id', 'id', and 'url' keys
    """
    async with aiohttp.ClientSession() as session:
        futures = []
        for _i, photo in enumerate(photos, start=1):
            photo_title = "{}_{}.jpg".format(photo["owner_id"], photo["id"])
            photo_path = photos_path.joinpath(photo_title)
            futures.append(download_photo(session, photo["url"], photo_path))

        for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
            await future


async def download_video(video_path: Path, video_link: str) -> None:
    """
    Download a video using yt-dlp.

    This function downloads a video from a VK video URL using yt-dlp library.
    The video is saved to the specified path with retry logic for reliability.

    Args:
        video_path: Path where to save the video file
        video_link: URL of the video to download from VK

    Note:
        Uses yt-dlp with quiet mode and 10 retries for robust downloading.
    """
    ydl_opts = {"outtmpl": f"{video_path}", "quiet": True, "retries": 10}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(video_link)
        print(f"Видео загружено: {video_link}")


async def download_videos(videos_path: Path, videos: list[dict[str, Any]]) -> None:
    """
    Download multiple videos concurrently.

    This function downloads multiple videos from VK concurrently using asyncio.
    Each video is downloaded using yt-dlp and saved with a filename based on
    owner_id and video_id.

    Args:
        videos_path: Directory path where to save video files
        videos: List of video dictionaries containing 'owner_id', 'id', and 'player' keys.
               The 'player' key contains the video URL for downloading.

    Note:
        Videos are downloaded concurrently with progress tracking using tqdm.
    """
    futures = []
    for _i, video in enumerate(videos, start=1):
        filename = "{}_{}.mp4".format(
            video["owner_id"], video["id"]
        )  # , video["title"])
        video_path = videos_path.joinpath(filename)
        futures.append(download_video(video_path, video["player"]))
    print(len(futures))
    for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
        await future
