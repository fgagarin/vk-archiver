"""File operation utilities.

Provides higher-level, safe filesystem primitives used by downloaders and
storage services, including atomic writes and YAML helpers.
"""

from pathlib import Path
from typing import Any

import yaml


class FileOperations:
    """Handles file and directory operations."""

    @staticmethod
    def create_dir(dir_path: Path) -> None:
        """
        Create directory if it doesn't exist.

        This method creates a directory at the specified path if it doesn't
        already exist. It creates all necessary parent directories as well.

        Args:
            dir_path: Path to the directory to create

        Note:
            Uses Path.mkdir() with parents=True and exist_ok=True to ensure
            the directory is created safely without raising exceptions if
            it already exists.
        """
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def atomic_write_bytes(target_path: Path, data: bytes) -> int:
        """Write bytes to a temp file and atomically rename into place.

        Args:
            target_path: Final destination path
            data: Bytes content to write
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
        tmp_path.replace(target_path)
        return len(data)

    @staticmethod
    def write_yaml(target_path: Path, payload: Any) -> int:
        """Write an object as YAML using atomic write.

        Args:
            target_path: Destination YAML file path
            payload: Serializable object
        """
        text = yaml.dump(payload, allow_unicode=True, indent=2)
        return FileOperations.atomic_write_bytes(target_path, text.encode("utf-8"))
