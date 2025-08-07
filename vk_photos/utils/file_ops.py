"""File operation utilities."""

from pathlib import Path


class FileOperations:
    """Handles file and directory operations."""

    @staticmethod
    def create_dir(dir_path: Path) -> None:
        """
        Create directory if it doesn't exist.

        Args:
            dir_path: Path to the directory to create
        """
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
