"""Downloader for VK community stories.

Step 8 from the group downloads plan:
- Fetch stories for the owner (community)
- Persist metadata to stories/stories.yaml
- Download media when URLs are available (mp4 for video, jpg for photo)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiohttp

from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations
from ..utils.logging_config import get_logger
from ..utils.state import TypeStateStore

logger = get_logger("downloaders.stories")


def _ext_from_url(url: str, default: str) -> str:
    path = url.split("?")[0]
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if 1 <= len(ext) <= 5 and all(c.isalnum() for c in ext):
            return ext
    return default


def _select_best_photo_url(photo_obj: dict[str, Any]) -> str | None:
    sizes = photo_obj.get("sizes") or []
    if not isinstance(sizes, list) or not sizes:
        return None
    best = sizes[-1]
    url = best.get("url")
    return url if isinstance(url, str) and url else None


def _select_best_video_url(video_obj: dict[str, Any]) -> str | None:
    # Stories video objects often contain files dict similar to normal videos
    files = video_obj.get("files") or video_obj.get("video_files") or {}
    if isinstance(files, dict):
        quality_order = [
            "mp4_2160",
            "mp4_1440",
            "mp4_1080",
            "mp4_720",
            "mp4_480",
            "mp4_360",
        ]
        for key in quality_order:
            url = files.get(key)
            if isinstance(url, str) and url:
                return url
        for _k, val in files.items():
            if isinstance(val, str) and val.startswith("http"):
                return val
    # Sometimes a direct URL might exist at top-level
    url = video_obj.get("url")
    if isinstance(url, str) and url:
        return url
    return None


class StoriesDownloader:
    """Downloads VK stories metadata and media when available.

    Returns a summary for observability.
    """

    def __init__(
        self,
        *,
        vk: RateLimitedVKAPI,
        utils: Utils,
        base_dir: Path,
        group_id: int,
        concurrency: int,
    ) -> None:
        """Initialize the stories downloader.

        Args:
            vk: Authenticated VK API client
            utils: Utilities facade
            base_dir: Group base directory
            group_id: Numeric group id
        """
        self._vk = vk
        self._utils = utils
        self._base_dir = base_dir
        self._group_id = group_id
        self._stories_dir = self._base_dir.joinpath("stories")
        self._files_dir = self._stories_dir.joinpath("files")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))
        self._concurrency = max(1, int(concurrency))

    def _collect_media_jobs(self, payload: dict[str, Any]) -> list[tuple[str, Path]]:
        jobs: list[tuple[str, Path]] = []
        items = payload.get("items")
        if not items:
            return jobs

        # VK returns items as a list of story bundles per owner; each has 'stories'
        for entry in items:
            stories = entry.get("stories") if isinstance(entry, dict) else None
            if not stories and isinstance(entry, dict):
                # Sometimes items themselves are stories
                stories = [entry]
            if not isinstance(stories, list):
                continue

            for story in stories:
                sid = int(story.get("id", 0))
                if sid == 0:
                    continue
                # Photo story
                if "photo" in story and isinstance(story["photo"], dict):
                    url = _select_best_photo_url(story["photo"])  # type: ignore[arg-type]
                    if url:
                        ext = _ext_from_url(url, "jpg")
                        jobs.append((url, self._files_dir.joinpath(f"{sid}.{ext}")))
                        continue
                # Video story
                if "video" in story and isinstance(story["video"], dict):
                    url = _select_best_video_url(story["video"])  # type: ignore[arg-type]
                    if url:
                        ext = _ext_from_url(url, "mp4")
                        jobs.append((url, self._files_dir.joinpath(f"{sid}.{ext}")))
                        continue
        return jobs

    async def run(self) -> dict[str, Any]:
        """Fetch currently available stories and write metadata and files.

        Returns:
            Summary dictionary with counts
        """
        self._utils.create_dir(self._stories_dir)
        self._utils.create_dir(self._files_dir)

        resp = await self._vk.call(
            "stories.get", owner_id=-self._group_id, _rl_timeout=15.0
        )

        # Persist raw payload
        FileOperations.write_yaml(self._stories_dir.joinpath("stories.yaml"), resp)

        # Collect media URLs and download directly when available
        jobs = self._collect_media_jobs(resp)
        if not jobs:
            logger.info("No downloadable story media URLs found")
            self._state.update("stories", {"last_run": True})
            return {"type": "stories", "items": 0, "files": 0, "failures": 0}

        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(self._concurrency)
            tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
            for url, target in jobs:
                if target.exists():
                    continue

                async def _bounded(url: str = url, target: Path = target) -> None:
                    async with sem:
                        await self._download_direct(session, url, target)

                tasks.append(_bounded())
            for t in asyncio.as_completed(tasks):
                await t

        logger.info("Saved %d stories media files", len(jobs))
        # Track that stories were fetched at least once
        self._state.update("stories", {"last_run": True})
        return {
            "type": "stories",
            "items": len(jobs),
            "files": len(jobs),
            "failures": 0,
        }

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
