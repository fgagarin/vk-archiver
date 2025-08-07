"""
Example integration of ConsistencyManager with downloader classes.

This module demonstrates how the ConsistencyManager can be integrated
with downloader classes to prevent duplicate downloads across multiple
program instances.
"""

import logging
from pathlib import Path

from vk_photos.utils.consistency import ConsistencyManager


class ExamplePhotoDownloader:
    """
    Example downloader class that integrates with ConsistencyManager.

    This class demonstrates how to use the ConsistencyManager to prevent
    duplicate downloads and ensure consistency across multiple instances.
    """

    def __init__(self, output_dir: Path, lock_file: Path | None = None) -> None:
        """
        Initialize the downloader with consistency management.

        Args:
            output_dir: Directory to save downloaded photos
            lock_file: Path to lock file for consistency management.
                      If None, uses output_dir/.downloads_lock.json
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if lock_file is None:
            lock_file = output_dir / ".downloads_lock.json"

        self.consistency_manager = ConsistencyManager(lock_file)
        logging.info(f"Initialized downloader with consistency manager: {lock_file}")

    def _generate_photo_id(self, photo_data: dict) -> str:
        """
        Generate a unique photo identifier.

        Args:
            photo_data: Photo data from VK API

        Returns:
            Unique photo identifier in format owner_id_photo_id
        """
        owner_id = photo_data.get("owner_id", 0)
        photo_id = photo_data.get("id", 0)
        return f"{owner_id}_{photo_id}"

    def _should_download_photo(self, photo_data: dict) -> bool:
        """
        Check if a photo should be downloaded.

        Args:
            photo_data: Photo data from VK API

        Returns:
            True if photo should be downloaded, False otherwise
        """
        photo_id = self._generate_photo_id(photo_data)

        # Check if already downloaded by any instance
        if self.consistency_manager.is_already_downloaded(photo_id):
            logging.info(f"Photo {photo_id} already downloaded, skipping")
            return False

        # Check if file already exists on disk
        filename = f"{photo_id}.jpg"
        filepath = self.output_dir / filename

        if filepath.exists():
            logging.info(f"File {filepath} already exists, marking as downloaded")
            self.consistency_manager.mark_as_downloaded(photo_id)
            return False

        return True

    def _mark_photo_downloaded(self, photo_data: dict) -> None:
        """
        Mark a photo as successfully downloaded.

        Args:
            photo_data: Photo data from VK API
        """
        photo_id = self._generate_photo_id(photo_data)
        self.consistency_manager.mark_as_downloaded(photo_id)
        logging.debug(f"Marked photo {photo_id} as downloaded")

    async def download_photos(self, photos: list[dict]) -> int:
        """
        Download a list of photos with consistency management.

        Args:
            photos: List of photo data from VK API

        Returns:
            Number of photos successfully downloaded
        """
        downloaded_count = 0

        for photo in photos:
            try:
                if not self._should_download_photo(photo):
                    continue

                # Simulate download process
                success = await self._download_single_photo(photo)

                if success:
                    self._mark_photo_downloaded(photo)
                    downloaded_count += 1
                    logging.info(
                        f"Successfully downloaded photo {self._generate_photo_id(photo)}"
                    )
                else:
                    logging.error(
                        f"Failed to download photo {self._generate_photo_id(photo)}"
                    )

            except Exception as e:
                logging.error(
                    f"Error downloading photo {self._generate_photo_id(photo)}: {e}"
                )
                continue

        logging.info(
            f"Downloaded {downloaded_count} new photos out of {len(photos)} total"
        )
        return downloaded_count

    async def _download_single_photo(self, photo_data: dict) -> bool:
        """
        Download a single photo (placeholder implementation).

        Args:
            photo_data: Photo data from VK API

        Returns:
            True if download was successful, False otherwise
        """
        # This is a placeholder - in real implementation, this would
        # download the actual photo from VK API
        photo_id = self._generate_photo_id(photo_data)
        filename = f"{photo_id}.jpg"
        filepath = self.output_dir / filename

        # Simulate download by creating an empty file
        try:
            filepath.touch()
            return True
        except Exception as e:
            logging.error(f"Failed to create file {filepath}: {e}")
            return False

    def get_download_stats(self) -> dict:
        """
        Get download statistics.

        Returns:
            Dictionary with download statistics
        """
        return {
            "total_downloaded": self.consistency_manager.get_downloaded_count(),
            "lock_file": str(self.consistency_manager.get_lock_file_path()),
            "output_dir": str(self.output_dir),
        }


# Example usage function
async def example_usage() -> None:
    """
    Example usage of the downloader with consistency management.
    """
    output_dir = Path("./downloads")
    downloader = ExamplePhotoDownloader(output_dir)

    # Simulate photo data from VK API
    sample_photos = [
        {"owner_id": 123456, "id": 789, "url": "https://example.com/photo1.jpg"},
        {"owner_id": 123456, "id": 790, "url": "https://example.com/photo2.jpg"},
        {"owner_id": 654321, "id": 123, "url": "https://example.com/photo3.jpg"},
    ]

    # Download photos
    await downloader.download_photos(sample_photos)

    # Get statistics
    stats = downloader.get_download_stats()
    logging.info(f"Download statistics: {stats}")

    # Running the same download again should skip all files
    downloaded_count_2 = await downloader.download_photos(sample_photos)
    logging.info(f"Second run downloaded {downloaded_count_2} photos (should be 0)")


if __name__ == "__main__":
    import asyncio

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run example
    asyncio.run(example_usage())
