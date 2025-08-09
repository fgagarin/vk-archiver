"""Downloader for VK community documents.

Implements Step 7 from the group downloads plan:
- Fetch documents via docs.get (owner_id = -group_id)
- Persist raw metadata to documents/docs.yaml
- Download files into documents/files/ with sanitized names
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
from tqdm.asyncio import tqdm

from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations
from ..utils.logging_config import get_logger
from ..utils.state import TypeStateStore

logger = get_logger("downloaders.documents")


def _sanitize_filename(name: str) -> str:
    """Sanitize a filename for safe filesystem usage.

    Args:
        name: Raw filename or title

    Returns:
        Sanitized string safe for file systems
    """
    return (
        name.replace("/", " ")
        .replace("\\", " ")
        .replace("|", " ")
        .replace(":", " ")
        .replace("*", " ")
        .replace("?", " ")
        .replace('"', " ")
        .replace("<", " ")
        .replace(">", " ")
        .strip()
    )


def _ext_from_doc(item: dict[str, Any]) -> str:
    """Best-effort extension from VK doc item; fall back to 'bin'."""
    ext = item.get("ext")
    if isinstance(ext, str) and 1 <= len(ext) <= 8:
        return ext.lower()
    return "bin"


@dataclass
class DocumentsRunParams:
    """Parameters controlling documents download scope."""

    max_items: int | None


class DocumentsDownloader:
    """Downloads VK documents metadata and files when available.

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
        """Initialize the documents downloader.

        Args:
            vk: Authenticated VK client
            utils: Utilities facade
            base_dir: Group base directory
            group_id: Numeric group id
            max_items: Optional cap for number of documents to process
        """
        self._vk = vk
        self._utils = utils
        self._base_dir = base_dir
        self._group_id = group_id
        self._params = DocumentsRunParams(max_items=max_items)
        self._docs_dir = self._base_dir.joinpath("documents")
        self._files_dir = self._docs_dir.joinpath("files")
        self._state = TypeStateStore(self._base_dir.joinpath("state.json"))
        self._concurrency = max(1, int(concurrency))

    async def _fetch_all_docs(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        existing = self._state.get("documents")
        offset = int(existing.get("offset", 0))
        count = 200
        while True:
            resp = await self._vk.call(
                "docs.get",
                owner_id=-self._group_id,
                count=count,
                offset=offset,
                _rl_timeout=25.0,
            )
            page = resp.get("items", [])
            if not page:
                break
            items.extend(page)
            if (
                self._params.max_items is not None
                and len(items) >= self._params.max_items
            ):
                items = items[: self._params.max_items]
                break
            if len(page) < count:
                break
            offset += count
            self._state.update("documents", {"offset": offset})
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

    async def run(self) -> dict[str, Any]:
        """Fetch documents, write metadata, and download files into documents/files.

        Returns:
            Summary dictionary with counts
        """
        self._utils.create_dir(self._docs_dir)
        self._utils.create_dir(self._files_dir)

        docs = await self._fetch_all_docs()
        FileOperations.write_yaml(self._docs_dir.joinpath("docs.yaml"), docs)

        # Download files when url is present
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(self._concurrency)
            tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
            pbar = tqdm(total=len(docs), desc="Documents", unit="file")
            for d in docs:
                url = d.get("url")
                if not isinstance(url, str) or not url:
                    continue
                doc_id = int(d.get("id"))
                title = _sanitize_filename(str(d.get("title", "document")))
                ext = _ext_from_doc(d)
                filename = f"{doc_id}_{title}.{ext}"
                target = self._files_dir.joinpath(filename)
                if target.exists():
                    continue

                async def _bounded(url: str = url, target: Path = target) -> None:
                    async with sem:
                        await self._download_direct(session, url, target)

                tasks.append(_bounded())

            for t in asyncio.as_completed(tasks):
                await t
                pbar.update(1)
            pbar.close()

        logger.info(
            "Saved %d documents metadata; attempted %d file downloads",
            len(docs),
            len(tasks),
        )
        return {
            "type": "documents",
            "items": len(docs),
            "file_download_attempts": len(tasks),
            "failures": 0,
        }
