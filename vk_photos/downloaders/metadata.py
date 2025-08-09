"""Downloader for community metadata.

Implements Step 3 from the group downloads plan:
- Fetch rich community metadata via groups.getById
- Persist raw response to metadata/group.yaml
- Update root meta.yaml with run parameters and timestamps
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..utils import RateLimitedVKAPI, Utils
from ..utils.file_ops import FileOperations


@dataclass
class MetadataRunConfig:
    """Run configuration to be recorded in root meta.yaml."""

    group_id: int
    screen_name: str
    types: list[str] | str
    output_dir: str
    since: str | None
    until: str | None
    max_items: int | None
    concurrency: int
    resume: bool
    api_version: str | None


class MetadataDownloader:
    """Downloads and persists VK community metadata."""

    def __init__(
        self,
        *,
        vk: RateLimitedVKAPI,
        utils: Utils,
        base_dir: Path,
        group_id: int,
        screen_name: str,
        run_config: MetadataRunConfig,
    ) -> None:
        """Initialize the downloader.

        Args:
            vk: Authenticated, rate-limited VK API instance
            utils: Shared utilities facade
            base_dir: Base directory for this group's downloads
            group_id: Numeric group id
            screen_name: Group screen name (may be empty)
            run_config: Parameters to record in root meta.yaml
        """
        self._vk = vk
        self._utils = utils
        self._base_dir = base_dir
        self._group_id = group_id
        self._screen_name = screen_name
        self._run_config = run_config

    async def run(self) -> None:
        """Fetch group metadata and write it to disk as YAML files."""
        # Ensure directories
        self._utils.create_dir(self._base_dir)
        metadata_dir = self._base_dir.joinpath("metadata")
        self._utils.create_dir(metadata_dir)

        # Fetch rich metadata
        fields = (
            "description,members_count,links,contacts,cover,site,activity,age_limits,"
            "ban_info,counters,place,verified,addresses,has_photo,photo_200,photo_max"
        )
        resp = await self._vk.call(
            "groups.getById", group_id=self._group_id, fields=fields
        )
        # Persist raw payload in metadata/group.yaml
        FileOperations.write_yaml(metadata_dir.joinpath("group.yaml"), resp)

        # Update root meta.yaml with run info
        meta_payload: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "vk_api_version": self._run_config.api_version,
            "group": {
                "id": self._group_id,
                "screen_name": self._screen_name,
            },
            "run": {
                "types": self._run_config.types,
                "since": self._run_config.since,
                "until": self._run_config.until,
                "max_items": self._run_config.max_items,
                "concurrency": self._run_config.concurrency,
                "resume": self._run_config.resume,
                "output_dir": self._run_config.output_dir,
            },
        }
        FileOperations.write_yaml(self._base_dir.joinpath("meta.yaml"), meta_payload)
