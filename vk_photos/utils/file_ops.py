"""File operation utilities."""

from pathlib import Path


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
