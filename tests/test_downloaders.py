"""Tests for downloader orchestration and path handling."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from vk_photos.downloaders.user import UserPhotoDownloader

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.mark.asyncio
async def test_user_downloader_builds_paths_and_invokes_download(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """It should resolve output directory and call shared download function with photos."""

    # Arrange VK and utils
    class DummyVK:
        async def call(self, method: str, **kwargs: Any) -> Any:  # noqa: D401
            if method == "users.get":
                return [
                    {
                        "first_name": "Ivan",
                        "last_name": "Petrov",
                        "sex": 2,
                        "is_closed": False,
                        "photo_max_orig": "https://example/photo.jpg",
                    }
                ]
            if method == "photos.get":
                return {"items": []}
            if method == "photos.getAll":
                return {"items": []}
            return {}

    class DummyUtils:
        def __init__(self) -> None:
            self._dir: Path | None = None

        async def get_username(self, user_id: str) -> str:  # noqa: D401
            return "Ivan Petrov"

        def create_dir(self, dir_path: Path) -> None:  # noqa: D401
            self._dir = dir_path
            dir_path.mkdir(parents=True, exist_ok=True)

    # Mock vk instance wrapper
    vk_instance = DummyVK()

    # Create utils instance to inject
    utils = DummyUtils()

    # Spy on download_photos
    # Spy on module-level function used by downloader
    from vk_photos.downloaders import user as user_mod

    download_spy = mocker.spy(user_mod, "download_photos")

    # Act
    downloader = UserPhotoDownloader(
        "123", vk_instance, utils=utils, parent_dir=tmp_path
    )
    await downloader.main()

    # Assert
    assert download_spy.call_count == 1
    call_args = download_spy.call_args[0]
    out_dir: Path = call_args[0]
    assert out_dir.exists(), "Downloader should create output directory"
