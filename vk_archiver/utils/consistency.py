"""
Consistency management for VK Archiver.

This module provides the ConsistencyManager class which handles file locking
and persistent storage of downloaded file lists to prevent duplicate downloads
across multiple program instances.
"""

import fcntl
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .logging_config import get_logger

logger = get_logger("utils.consistency")


class ConsistencyManager:
    """
    Manages download consistency across multiple program instances.

        This class implements file locking and persistent storage to ensure that
        downloaded files are tracked consistently across multiple instances of
        the VK Archiver. It prevents duplicate downloads and maintains
    a persistent record of all downloaded files.

    Attributes:
        lock_file (Path): Path to the file used for storing download records
        downloaded_files (Set[str]): Set of already downloaded file identifiers
        lock_handle (Optional[Any]): File handle for locking operations
    """

    def __init__(self, lock_file: Path) -> None:
        """
        Initialize the ConsistencyManager.

        Args:
            lock_file: Path to the file used for storing download records.
                      This file will be created if it doesn't exist.
        """
        self.lock_file = lock_file
        self.downloaded_files: set[str] = set()
        self.lock_handle: Any | None = None
        self._load_downloaded_files()
        logger.info(f"ConsistencyManager initialized with lock file: {lock_file}")

    def _load_downloaded_files(self) -> None:
        """
        Load list of downloaded files from persistent storage.

        This method reads the lock file with a shared lock to get the list
        of already downloaded files. If the file doesn't exist or is corrupted,
        it starts with an empty set.
        """
        if not self.lock_file.exists():
            logger.info(
                f"Lock file does not exist, starting with empty download list: {self.lock_file}"
            )
            return

        try:
            with open(self.lock_file, encoding="utf-8") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    self.downloaded_files = set(data.get("downloaded_files", []))
                    last_updated = data.get("last_updated", "unknown")
                    logger.info(
                        f"Loaded {len(self.downloaded_files)} downloaded files from {last_updated}"
                    )
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                f"Could not load downloaded files list from {self.lock_file}: {e}"
            )
            logger.info("Starting with empty download list")
            self.downloaded_files = set()

    def _save_downloaded_files(self) -> None:
        """
        Save list of downloaded files to persistent storage.

        This method writes the current list of downloaded files to the lock file
        with an exclusive lock to prevent race conditions. It also includes
        metadata about when the file was last updated.
        """
        try:
            # Ensure the directory exists
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.lock_file, "w", encoding="utf-8") as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    data = {
                        "downloaded_files": list(self.downloaded_files),
                        "last_updated": datetime.now().isoformat(),
                        "total_files": len(self.downloaded_files),
                    }
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()  # Ensure data is written to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            logger.debug(
                f"Saved {len(self.downloaded_files)} downloaded files to {self.lock_file}"
            )
        except OSError as e:
            logger.error(
                f"Could not save downloaded files list to {self.lock_file}: {e}"
            )
            raise

    def is_already_downloaded(self, photo_id: str) -> bool:
        """
        Check if a photo is already downloaded by any instance.

        Args:
            photo_id: Unique identifier for the photo (format: owner_id_photo_id)

        Returns:
            True if the photo is already downloaded, False otherwise
        """
        is_downloaded = photo_id in self.downloaded_files
        if is_downloaded:
            logger.debug(f"Photo {photo_id} already downloaded, skipping")
        return is_downloaded

    def mark_as_downloaded(self, photo_id: str) -> None:
        """
        Mark a photo as downloaded and persist the information.

        This method adds the photo ID to the downloaded files set and
        immediately saves the updated list to persistent storage.

        Args:
            photo_id: Unique identifier for the photo (format: owner_id_photo_id)
        """
        if photo_id not in self.downloaded_files:
            self.downloaded_files.add(photo_id)
            self._save_downloaded_files()
            logger.debug(f"Marked photo {photo_id} as downloaded")
        else:
            logger.debug(f"Photo {photo_id} already marked as downloaded")

    def get_downloaded_count(self) -> int:
        """
        Get the total number of downloaded files.

        Returns:
            Number of files that have been downloaded
        """
        return len(self.downloaded_files)

    def get_downloaded_files(self) -> set[str]:
        """
        Get a copy of the set of downloaded file identifiers.

        Returns:
            Set of downloaded file identifiers
        """
        return self.downloaded_files.copy()

    def clear_downloaded_files(self) -> None:
        """
        Clear all downloaded files from the record.

        This method removes all entries from the downloaded files set and
        saves the empty list to persistent storage. Use with caution.
        """
        self.downloaded_files.clear()
        self._save_downloaded_files()
        logger.info("Cleared all downloaded files from consistency record")

    def remove_downloaded_file(self, photo_id: str) -> bool:
        """
        Remove a specific photo from the downloaded files record.

        Args:
            photo_id: Unique identifier for the photo to remove

        Returns:
            True if the photo was removed, False if it wasn't in the list
        """
        if photo_id in self.downloaded_files:
            self.downloaded_files.remove(photo_id)
            self._save_downloaded_files()
            logger.info(f"Removed photo {photo_id} from downloaded files record")
            return True
        else:
            logger.debug(f"Photo {photo_id} not found in downloaded files record")
            return False

    def get_lock_file_path(self) -> Path:
        """
        Get the path to the lock file.

        Returns:
            Path to the lock file
        """
        return self.lock_file

    def __enter__(self) -> "ConsistencyManager":
        """
        Context manager entry point.

        Returns:
            Self for use in context manager
        """
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None
    ) -> None:
        """
        Context manager exit point.

        Ensures that any pending changes are saved when exiting the context.
        """
        if exc_type is not None:
            logger.error(f"Exception occurred in ConsistencyManager context: {exc_val}")
        # Ensure final save
        if self.downloaded_files:
            self._save_downloaded_files()
