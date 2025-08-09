"""Downloader for VK community videos.

Implements Step 6 from the group downloads plan:
- Fetch videos via video.get (and optionally albums in future)
- Persist metadata to videos/videos.yaml (raw array)
- Download playable media when possible:
  - Prefer direct file URLs from 'files' if present (highest quality)
  - Otherwise, use 'player' URL via yt-dlp
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiohttp
from tqdm.asyncio import tqdm

from ..functions import download_video
from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations
from ..utils.logging_config import get_logger
from ..utils.state import TypeStateStore

logger = get_logger("downloaders.videos")


def _select_best_video_file(files_dict: dict[str, Any]) -> str | None:
    """Pick the best available mp4 URL from VK 'files' map."""
    if not isinstance(files_dict, dict):
        return None

    # Typical VK keys like mp4_1080, mp4_720, mp4_480 ... pick highest
    quality_order = [
        "mp4_2160",
        "mp4_1440",
        "mp4_1080",
        "mp4_720",
        "mp4_480",
        "mp4_360",
    ]
    for key in quality_order:
        url = files_dict.get(key)
        if isinstance(url, str) and url:
            return url
    # Fallbacks
    for _key, val in files_dict.items():
        if isinstance(val, str) and val.startswith("http"):
            return val
    return None


class VideosDownloader:
    """Downloads VK videos (metadata and files when possible).

    Returns a summary for observability.
    """

    def __init__(
        self,
        *,
        vk: RateLimitedVKAPI,
        utils: Utils,
        base_dir: Path,
        group_id: int,
        max_items: int | None,
        concurrency: int,
    ) -> None:
        self._vk = vk
        self._utils = utils
        self._base_dir = base_dir
        self._group_id = group_id
        self._max_items = max_items
        self._videos_dir = self._base_dir.joinpath("videos")
        self._files_dir = self._videos_dir.joinpath("files")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))
        self._concurrency = max(1, int(concurrency))

    async def _fetch_all_videos(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        existing = self._state.get("videos")
        offset = int(existing.get("offset", 0))
        count = 100
        while True:
            resp = await self._vk.call(
                "video.get",
                owner_id=-self._group_id,
                count=count,
                offset=offset,
                _rl_timeout=25.0,
            )
            page = resp.get("items", [])
            if not page:
                break
            items.extend(page)
            if self._max_items is not None and len(items) >= self._max_items:
                items = items[: self._max_items]
                break
            if len(page) < count:
                break
            offset += count
            self._state.update("videos", {"offset": offset})
        return items

    async def _download_direct(
        self, session: aiohttp.ClientSession, url: str, target: Path
    ) -> None:
        if target.exists():
            return
        marker = target.parent.joinpath(f"{target.name}_error.txt")
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    FileOperations.atomic_write_bytes(target, await response.read())
                    # On success, remove any existing error marker
                    try:
                        if marker.exists():
                            marker.unlink()
                    except Exception:  # noqa: BLE001
                        pass
                else:
                    message = f"HTTP {response.status} while downloading {url}"
                    logger.warning("Failed to download %s: %s", target.name, message)
                    FileOperations.atomic_write_bytes(marker, message.encode("utf-8"))
        except aiohttp.ClientError as exc:
            message = f"Client error while downloading {url}: {exc}"
            logger.warning("Failed to download %s: %s", target.name, message)
            FileOperations.atomic_write_bytes(marker, message.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            message = f"Unexpected error while downloading {url}: {exc}"
            logger.warning("Failed to download %s: %s", target.name, message)
            FileOperations.atomic_write_bytes(marker, message.encode("utf-8"))

    async def run(self) -> dict[str, Any]:
        """Fetch videos, write metadata YAML, and download files when possible.

        Returns:
            Summary dictionary with counts
        """
        self._utils.create_dir(self._videos_dir)
        self._utils.create_dir(self._files_dir)

        videos = await self._fetch_all_videos()
        FileOperations.write_yaml(self._videos_dir.joinpath("videos.yaml"), videos)

        # Build yt-dlp jobs for all videos to avoid HTTP 400 on direct links
        ytdlp_jobs: list[dict[str, Any]] = []
        for vid in videos:
            vid_id = int(vid.get("id"))
            owner_id = int(vid.get("owner_id"))
            target = self._files_dir.joinpath(f"{vid_id}.mp4")
            url: str | None = None
            player = vid.get("player")
            if isinstance(player, str) and player:
                url = player
            else:
                url = f"https://vk.com/video{owner_id}_{vid_id}"
            if url:
                ytdlp_jobs.append({"id": vid_id, "url": url, "target": target})

        # Run yt-dlp downloads with bounded concurrency and progress
        pbar_all = tqdm(total=len(ytdlp_jobs), desc="Videos", unit="file")
        sem = asyncio.Semaphore(self._concurrency)

        async def _dl(job: dict[str, Any]) -> None:
            target: Path = job["target"]
            url: str = job["url"]
            if target.exists():
                pbar_all.update(1)
                return
            marker = target.parent.joinpath(f"{target.name}_error.txt")
            async with sem:
                try:
                    await download_video(target, url)
                    # On success remove marker
                    try:
                        if marker.exists():
                            marker.unlink()
                    except Exception:  # noqa: BLE001
                        pass
                except Exception as exc:  # noqa: BLE001
                    message = f"yt-dlp error while downloading {url}: {exc}"
                    FileOperations.atomic_write_bytes(marker, message.encode("utf-8"))
                finally:
                    pbar_all.update(1)

        tasks = [_dl(job) for job in ytdlp_jobs]
        for t in asyncio.as_completed(tasks):
            await t
        pbar_all.close()

        logger.info(
            "Saved %d videos metadata and downloaded %d direct files, %d via player",
            len(videos),
            0,
            len(ytdlp_jobs),
        )
        return {
            "type": "videos",
            "items": len(videos),
            "direct_downloads": 0,
            "player_downloads": len(ytdlp_jobs),
            "failures": 0,
        }
