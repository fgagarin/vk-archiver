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
    """Downloads VK videos (metadata and files when possible)."""

    def __init__(
        self,
        *,
        vk: RateLimitedVKAPI,
        utils: Utils,
        base_dir: Path,
        group_id: int,
        max_items: int | None,
    ) -> None:
        self._vk = vk
        self._utils = utils
        self._base_dir = base_dir
        self._group_id = group_id
        self._max_items = max_items
        self._videos_dir = self._base_dir.joinpath("videos")
        self._files_dir = self._videos_dir.joinpath("files")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))

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
        async with session.get(url) as response:
            if response.status == 200:
                FileOperations.atomic_write_bytes(target, await response.read())
            else:
                logger.warning(
                    "Failed to download %s: HTTP %s", target.name, response.status
                )

    async def run(self) -> None:
        """Fetch videos, write metadata YAML, and download files when possible."""
        self._utils.create_dir(self._videos_dir)
        self._utils.create_dir(self._files_dir)

        videos = await self._fetch_all_videos()
        FileOperations.write_yaml(self._videos_dir.joinpath("videos.yaml"), videos)

        # Prepare download tasks: prefer 'files' entry else 'player' with yt-dlp
        direct_downloads: list[tuple[str, Path]] = []
        ytdlp_jobs: list[dict[str, Any]] = []
        for vid in videos:
            vid_id = int(vid.get("id"))
            owner_id = int(vid.get("owner_id"))
            target = self._files_dir.joinpath(f"{vid_id}.mp4")
            files_url = _select_best_video_file(vid.get("files") or {})
            if files_url:
                direct_downloads.append((files_url, target))
            else:
                player = vid.get("player")
                if isinstance(player, str) and player:
                    ytdlp_jobs.append(
                        {"owner_id": owner_id, "id": vid_id, "player": player}
                    )

        # Run direct downloads
        async with aiohttp.ClientSession() as session:
            tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
            for url, path in direct_downloads:
                if path.exists():
                    continue
                tasks.append(self._download_direct(session, url, path))
            for t in asyncio.as_completed(tasks):
                await t

        # Run yt-dlp downloads (sequential via helper for now)
        for job in ytdlp_jobs:
            target = self._files_dir.joinpath(f"{job['id']}.mp4")
            if target.exists():
                continue
            await download_video(target, job["player"])  # uses retries internally

        logger.info(
            "Saved %d videos metadata and downloaded %d direct files, %d via player",
            len(videos),
            len(direct_downloads),
            len(ytdlp_jobs),
        )
