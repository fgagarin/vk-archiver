"""
Tests for the ConsistencyManager class.

This module contains unit tests for the ConsistencyManager class to ensure
it properly handles file locking and persistent storage of downloaded file lists.
"""

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest

from vk_photos.utils.consistency import ConsistencyManager

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from _pytest.monkeypatch import MonkeyPatch


class TestConsistencyManager:
    """Test cases for ConsistencyManager class."""

    @pytest.fixture
    def temp_lock_file(self) -> Generator[Path, None, None]:
        """
        Create a temporary lock file for testing.

        Returns:
            Path to temporary lock file
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_initialization_with_new_file(self, temp_lock_file: Path) -> None:
        """Test ConsistencyManager initialization with non-existent lock file."""
        manager = ConsistencyManager(temp_lock_file)

        assert manager.lock_file == temp_lock_file
        assert len(manager.downloaded_files) == 0
        assert manager.get_downloaded_count() == 0

    def test_initialization_with_existing_file(self, temp_lock_file: Path) -> None:
        """Test ConsistencyManager initialization with existing lock file."""
        # Create existing lock file with some data
        existing_data = {
            'downloaded_files': ['123_456', '789_012'],
            'last_updated': '2023-01-01T00:00:00',
            'total_files': 2
        }

        with open(temp_lock_file, 'w') as f:
            json.dump(existing_data, f)

        manager = ConsistencyManager(temp_lock_file)

        assert '123_456' in manager.downloaded_files
        assert '789_012' in manager.downloaded_files
        assert manager.get_downloaded_count() == 2

    def test_mark_as_downloaded(self, temp_lock_file: Path) -> None:
        """Test marking files as downloaded."""
        manager = ConsistencyManager(temp_lock_file)

        # Mark a file as downloaded
        manager.mark_as_downloaded('123_456')

        assert '123_456' in manager.downloaded_files
        assert manager.get_downloaded_count() == 1
        assert manager.is_already_downloaded('123_456')

    def test_mark_as_downloaded_duplicate(self, temp_lock_file: Path) -> None:
        """Test marking the same file as downloaded multiple times."""
        manager = ConsistencyManager(temp_lock_file)

        # Mark the same file twice
        manager.mark_as_downloaded('123_456')
        manager.mark_as_downloaded('123_456')

        assert '123_456' in manager.downloaded_files
        assert manager.get_downloaded_count() == 1  # Should still be 1

    def test_is_already_downloaded(self, temp_lock_file: Path) -> None:
        """Test checking if files are already downloaded."""
        manager = ConsistencyManager(temp_lock_file)

        # Initially no files are downloaded
        assert not manager.is_already_downloaded('123_456')

        # Mark as downloaded
        manager.mark_as_downloaded('123_456')
        assert manager.is_already_downloaded('123_456')

    def test_get_downloaded_files(self, temp_lock_file: Path) -> None:
        """Test getting the set of downloaded files."""
        manager = ConsistencyManager(temp_lock_file)

        # Add some files
        manager.mark_as_downloaded('123_456')
        manager.mark_as_downloaded('789_012')

        downloaded_files = manager.get_downloaded_files()

        assert isinstance(downloaded_files, set)
        assert '123_456' in downloaded_files
        assert '789_012' in downloaded_files
        assert len(downloaded_files) == 2

    def test_remove_downloaded_file(self, temp_lock_file: Path) -> None:
        """Test removing a file from the downloaded list."""
        manager = ConsistencyManager(temp_lock_file)

        # Add a file
        manager.mark_as_downloaded('123_456')
        assert manager.get_downloaded_count() == 1

        # Remove the file
        result = manager.remove_downloaded_file('123_456')
        assert result is True
        assert manager.get_downloaded_count() == 0
        assert not manager.is_already_downloaded('123_456')

    def test_remove_nonexistent_file(self, temp_lock_file: Path) -> None:
        """Test removing a file that doesn't exist in the list."""
        manager = ConsistencyManager(temp_lock_file)

        result = manager.remove_downloaded_file('123_456')
        assert result is False

    def test_clear_downloaded_files(self, temp_lock_file: Path) -> None:
        """Test clearing all downloaded files."""
        manager = ConsistencyManager(temp_lock_file)

        # Add some files
        manager.mark_as_downloaded('123_456')
        manager.mark_as_downloaded('789_012')
        assert manager.get_downloaded_count() == 2

        # Clear all files
        manager.clear_downloaded_files()
        assert manager.get_downloaded_count() == 0

    def test_context_manager(self, temp_lock_file: Path) -> None:
        """Test ConsistencyManager as a context manager."""
        with ConsistencyManager(temp_lock_file) as manager:
            manager.mark_as_downloaded('123_456')
            assert manager.get_downloaded_count() == 1

        # After context exit, data should still be persisted
        manager2 = ConsistencyManager(temp_lock_file)
        assert manager2.get_downloaded_count() == 1
        assert manager2.is_already_downloaded('123_456')

    def test_persistence_across_instances(self, temp_lock_file: Path) -> None:
        """Test that data persists across different ConsistencyManager instances."""
        # First instance
        manager1 = ConsistencyManager(temp_lock_file)
        manager1.mark_as_downloaded('123_456')
        manager1.mark_as_downloaded('789_012')

        # Second instance should see the same data
        manager2 = ConsistencyManager(temp_lock_file)
        assert manager2.get_downloaded_count() == 2
        assert manager2.is_already_downloaded('123_456')
        assert manager2.is_already_downloaded('789_012')

    def test_corrupted_lock_file(self, temp_lock_file: Path) -> None:
        """Test handling of corrupted lock file."""
        # Create a corrupted JSON file
        with open(temp_lock_file, 'w') as f:
            f.write('invalid json content')

        # Should handle gracefully and start with empty set
        manager = ConsistencyManager(temp_lock_file)
        assert manager.get_downloaded_count() == 0
        assert len(manager.downloaded_files) == 0
