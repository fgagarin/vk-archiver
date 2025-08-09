"""Downloader for wall content of a VK community.

Step 4 from the group downloads plan:
- Iterate wall.get pages until done or max-items reached
- Apply since/until date filtering
- Write posts to wall/posts.yaml
- Optionally extract attachments to wall/attachments/photos/links.yaml
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from tqdm.asyncio import tqdm

from ..functions import download_photo, download_photos
from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations
from ..utils.logging_config import get_logger
from ..utils.state import TypeStateStore

logger = get_logger("downloaders.wall")


def _parse_date(date_str: str | None) -> int | None:
    """Parse a YYYY-MM-DD date string to UTC unix timestamp.

    Args:
        date_str: Date in YYYY-MM-DD format or None

    Returns:
        Unix timestamp (int) in UTC or None if input is None
    """
    if not date_str:
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _format_day(ts: int) -> str:
    """Format unix timestamp to YYYY-MM-DD (UTC)."""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def _ext_from_url(url: str) -> str:
    """Best-effort extension from URL path; defaults to jpg."""
    path = url.split("?")[0]
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if 1 <= len(ext) <= 5 and all(c.isalnum() for c in ext):
            return ext
    return "jpg"


@dataclass
class WallRunParams:
    """Parameters controlling the wall download run."""

    max_items: int | None
    since_utc_ts: int | None
    until_utc_ts: int | None


class WallDownloader:
    """Downloads wall posts for a VK community and saves as YAML.

    Returns a summary for observability.
    """

    def __init__(
        self,
        *,
        vk: RateLimitedVKAPI,
        utils: Utils,
        base_dir: Path,
        group_id: int,
        since: str | None,
        until: str | None,
        max_items: int | None,
    ) -> None:
        """Initialize the wall downloader.

        Args:
            vk: Authenticated VK API client
            utils: Utilities facade
            base_dir: Group base directory
            group_id: Numeric group id
            since: Only include posts on/after this date (YYYY-MM-DD)
            until: Only include posts on/before this date (YYYY-MM-DD)
            max_items: Limit of posts to persist (after filtering). None means all
        """
        self._vk = vk
        self._utils = utils
        self._group_id = group_id
        self._base_dir = base_dir
        self._params = WallRunParams(
            max_items=max_items,
            since_utc_ts=_parse_date(since),
            until_utc_ts=_parse_date(until),
        )

        # Paths
        self._wall_dir = self._base_dir.joinpath("wall")
        self._attachments_dir = self._wall_dir.joinpath("attachments")
        self._attachments_photos_dir = self._attachments_dir.joinpath("photos")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))

    def _post_passes_filters(self, post: dict[str, Any]) -> bool:
        ts = int(post.get("date", 0))
        if self._params.since_utc_ts is not None and ts < self._params.since_utc_ts:
            return False
        if self._params.until_utc_ts is not None and ts > self._params.until_utc_ts:
            return False
        return True

    @staticmethod
    def _extract_photo_attachments(post: dict[str, Any]) -> list[dict[str, Any]]:
        photos: list[dict[str, Any]] = []
        attachments = post.get("attachments")
        if not isinstance(attachments, list):
            return photos
        for att in attachments:
            if att.get("type") == "photo":
                photo = att.get("photo", {})
                sizes = photo.get("sizes") or []
                if not sizes:
                    continue
                best = sizes[-1]
                url = best.get("url")
                if not url:
                    continue
                photos.append(
                    {
                        "post_id": post.get("id"),
                        "photo_id": photo.get("id"),
                        "owner_id": photo.get("owner_id"),
                        "url": url,
                    }
                )
        return photos

    async def run(self) -> dict[str, Any]:
        """Fetch posts and persist them under wall/ as YAML files.

        Returns:
            Summary dictionary with counts
        """
        # Ensure directories
        self._utils.create_dir(self._wall_dir)
        self._utils.create_dir(self._attachments_photos_dir)

        posts: list[dict[str, Any]] = []
        photos_index: list[dict[str, Any]] = []

        # Resume offset if present
        existing = self._state.get("wall")
        offset = int(existing.get("offset", 0))
        count = 100
        saved = 0
        total_posts: int | None = None

        pbar = None
        while True:
            resp = await self._vk.call(
                "wall.get",
                owner_id=-self._group_id,
                count=count,
                offset=offset,
                _rl_timeout=20.0,
            )
            if total_posts is None:
                total_posts = int(resp.get("count", 0))
                pbar = tqdm(total=total_posts or None, desc="Wall posts", unit="post")
            items: list[dict[str, Any]] = resp.get("items", [])

            if not items:
                break

            # If data are in reverse chronological order (typical), we can
            # short-circuit when the last item falls before since-date filter
            if self._params.since_utc_ts is not None:
                last_ts = int(items[-1].get("date", 0))
                if last_ts < self._params.since_utc_ts:
                    logger.info(
                        "Reached posts older than --since. Stopping pagination."
                    )
                    # Still process current page with filtering
                    items = [p for p in items if self._post_passes_filters(p)]
                    for post in items:
                        posts.append(post)
                        photos_index.extend(self._extract_photo_attachments(post))
                        saved += 1
                        if (
                            self._params.max_items is not None
                            and saved >= self._params.max_items
                        ):
                            break
                    break

            for post in items:
                if not self._post_passes_filters(post):
                    continue
                posts.append(post)
                photos_index.extend(self._extract_photo_attachments(post))
                saved += 1
                if pbar is not None:
                    pbar.update(1)
                if (
                    self._params.max_items is not None
                    and saved >= self._params.max_items
                ):
                    break

            if self._params.max_items is not None and saved >= self._params.max_items:
                break

            if len(items) < count:
                break

            offset += count
            # Persist resume point
            self._state.update("wall", {"offset": offset})
            # Log progress every page
            logger.info(
                f"Wall pagination: saved={saved}, offset={offset}, total={total_posts}"
            )

        # Close progress bar
        if pbar is not None:
            pbar.close()

        # Close progress bar
        if pbar is not None:
            pbar.close()

        # Persist posts and attachments index
        FileOperations.write_yaml(self._wall_dir.joinpath("posts.yaml"), posts)
        if photos_index:
            FileOperations.write_yaml(
                self._attachments_photos_dir.joinpath("links.yaml"), photos_index
            )
            # Also download all wall photo files into attachments/photos directory
            photos_for_download: list[dict[str, Any]] = [
                {
                    "owner_id": item.get("owner_id"),
                    "id": item.get("photo_id"),
                    "url": item.get("url"),
                }
                for item in photos_index
                if item.get("url") and item.get("photo_id") is not None
            ]
            if photos_for_download:
                await download_photos(self._attachments_photos_dir, photos_for_download)

        # Write per-post text files and co-located attachments
        posts_dir = self._wall_dir.joinpath("by_post")
        self._utils.create_dir(posts_dir)

        # Map post_id -> YYYY-MM-DD
        post_id_to_date: dict[int, str] = {
            int(p.get("id")): _format_day(int(p.get("date", 0))) for p in posts
        }

        # Save each post text
        for post in posts:
            pid = int(post.get("id"))
            day = post_id_to_date.get(pid, _format_day(int(post.get("date", 0))))
            text_content = str(post.get("text") or "")
            text_path = posts_dir.joinpath(f"{day}-{pid}.txt")
            FileOperations.atomic_write_bytes(text_path, text_content.encode("utf-8"))

        # Download per-post photo attachments into the same directory with naming rule
        photo_jobs: list[tuple[str, Path]] = []
        for item in photos_index:
            url = item.get("url")
            post_id = item.get("post_id")
            photo_id = item.get("photo_id")
            if not (
                isinstance(url, str)
                and url
                and isinstance(post_id, int)
                and photo_id is not None
            ):
                continue
            day = post_id_to_date.get(int(post_id), "unknown")
            ext = _ext_from_url(url)
            target = posts_dir.joinpath(f"{day}-{post_id}-{photo_id}.{ext}")
            if target.exists():
                continue
            photo_jobs.append((url, target))

        if photo_jobs:
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(8)

                async def _bounded(url: str, dest: Path) -> None:
                    async with sem:
                        await download_photo(session, url, dest)

                tasks = [_bounded(url, dest) for (url, dest) in photo_jobs]
                for t in asyncio.as_completed(tasks):
                    try:
                        await t
                    except Exception:
                        pass

        logger.info(
            f"Saved {len(posts)} posts and {len(photos_index)} photo links for group {self._group_id}"
        )
        return {
            "type": "wall",
            "items": len(posts),
            "photo_links": len(photos_index),
            "failures": 0,
        }
