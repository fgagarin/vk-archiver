"""Tests for utility classes: FileOperations and RateLimitedVKAPI basics."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from vk_photos.utils.file_ops import FileOperations

if TYPE_CHECKING:
    pass


def test_file_operations_create_dir(tmp_path: Path) -> None:
    """It should create the directory if it does not exist."""
    to_create = tmp_path / "nested" / "dir"
    assert not to_create.exists()

    FileOperations.create_dir(to_create)

    assert to_create.exists()
    assert to_create.is_dir()
