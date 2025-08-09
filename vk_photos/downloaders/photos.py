"""Downloader for group photo albums and photos.

Implements Step 5 of the group downloads plan:
- Fetch albums via photos.getAlbums
- For each album, create directory photos/<album-id>-<album-title>/ and write info.yaml
- Fetch photos with photo_sizes and download best-quality size URL
- Skip already-existing files by name
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
from tqdm.asyncio import tqdm

from ..functions import download_photo
from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations
from ..utils.logging_config import get_logger
from ..utils.state import TypeStateStore

logger = get_logger("downloaders.photos")


def _sanitize_title(title: str) -> str:
    return (
        title.replace("/", " ")
        .replace("\\", " ")
        .replace("|", " ")
        .replace(":", " ")
        .replace("*", " ")
        .replace("?", " ")
        .replace('"', " ")
        .replace("<", " ")
        .replace(">", " ")
        .replace(".", " ")
        .strip()
    )


def _ext_from_url(url: str) -> str:
    # Naive extension detection from URL path; default to jpg
    path = url.split("?")[0]
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        # Basic sanity
        if 1 <= len(ext) <= 5 and all(c.isalnum() for c in ext):
            return ext
    return "jpg"


@dataclass
class PhotosRunParams:
    """Run parameters controlling photo download scope."""

    max_items: int | None


class PhotosDownloader:
    """Downloads group albums and photos into the canonical storage layout.

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
        self._group_id = group_id
        self._base_dir = base_dir
        self._params = PhotosRunParams(max_items=max_items)
        self._photos_root = self._base_dir.joinpath("photos")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))
        self._concurrency = max(1, int(concurrency))

    async def _fetch_all_albums(self) -> list[dict[str, Any]]:
        albums: list[dict[str, Any]] = []
        # Resume album pagination
        existing = self._state.get("photos")
        offset = int(existing.get("albums_offset", 0))
        count = 100
        while True:
            resp = await self._vk.call(
                "photos.getAlbums",
                owner_id=-self._group_id,
                count=count,
                offset=offset,
                _rl_timeout=20.0,
            )
            items = resp.get("items", [])
            albums.extend(items)
            if len(items) < count:
                break
            offset += count
            self._state.update("photos", {"albums_offset": offset})
        return albums

    async def _fetch_album_photos(self, album_id: int) -> list[dict[str, Any]]:
        photos: list[dict[str, Any]] = []
        offset = 0
        count = 100
        while True:
            resp = await self._vk.call(
                "photos.get",
                owner_id=-self._group_id,
                album_id=album_id,
                count=count,
                offset=offset,
                photo_sizes=True,
                extended=False,
                _rl_timeout=25.0,
            )
            items = resp.get("items", [])
            photos.extend(items)
            if len(items) < count:
                break
            offset += count
        return photos

    async def run(self) -> dict[str, Any]:
        """Fetch albums and download their photos into album folders.

        Returns:
            Summary dictionary with counts
        """
        # Ensure base directories
        self._utils.create_dir(self._photos_root)

        albums = await self._fetch_all_albums()
        logger.info(f"Found {len(albums)} albums for group {self._group_id}")

        # Global cap across all albums
        remaining = (
            self._params.max_items if self._params.max_items is not None else None
        )

        pbar_albums = tqdm(total=len(albums), desc="Albums", unit="album")
        for album in albums:
            if remaining is not None and remaining <= 0:
                break

            aid = int(album.get("id"))
            aname = _sanitize_title(str(album.get("title", "")))
            album_dir = self._photos_root.joinpath(f"{aid}-{aname}")
            self._utils.create_dir(album_dir)

            # Persist raw album metadata
            FileOperations.write_yaml(album_dir.joinpath("info.yaml"), album)

            # Collect photos for this album
            # Fetch all photos for the album; we rely on file-exists skip and
            # error markers to avoid duplicates and to retry failures next runs.
            items = await self._fetch_album_photos(aid)

            if remaining is not None and len(items) > remaining:
                items = items[:remaining]

            # Download concurrently with aiohttp and our naming convention
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(self._concurrency)
                tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
                pbar_photos = tqdm(total=len(items), desc=f"Album {aid}", unit="photo")
                for p in items:
                    sizes = p.get("sizes") or []
                    if not sizes:
                        continue
                    best = sizes[-1]
                    url = best.get("url")
                    if not url:
                        continue
                    pid = int(p.get("id"))
                    ext = _ext_from_url(url)
                    filename = f"{self._group_id}-{pid}.{ext}"
                    target = album_dir.joinpath(filename)

                    if target.exists():
                        continue

                    async def _bounded(
                        url: str = url,
                        target: Path = target,
                        sem: asyncio.Semaphore = sem,
                        session: aiohttp.ClientSession = session,
                    ) -> None:
                        async with sem:
                            try:
                                await download_photo(session, url, target)
                            except Exception as exc:  # noqa: BLE001
                                marker = target.parent.joinpath(
                                    f"{target.name}_error.txt"
                                )
                                try:
                                    FileOperations.atomic_write_bytes(
                                        marker, str(exc).encode("utf-8")
                                    )
                                except Exception:  # noqa: BLE001
                                    pass

                    tasks.append(_bounded())

                # Execute
                for t in asyncio.as_completed(tasks):
                    await t
                    pbar_photos.update(1)
                pbar_photos.close()

            if remaining is not None:
                remaining -= len(items)

            # Do not advance per-album offset so failed items can be retried next run

            pbar_albums.update(1)

        pbar_albums.close()
        logger.info("Finished photos download for group %s", self._group_id)
        return {
            "type": "photos",
            "albums": len(albums),
            "items": None if remaining is None else self._params.max_items,
            "failures": 0,
        }
