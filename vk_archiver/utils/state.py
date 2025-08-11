"""Simple JSON state store for per-type resume cursors.

The state is kept under a single file at the group base directory, typically
``<group_dir>/state.json`` with the schema::

    {
      "wall": {"offset": 0, "last_post_id": 123},
      "photos": {"last_album_id": 456, "album_offset": 200},
      "videos": {"offset": 100},
      "documents": {"offset": 300}
    }

Each downloader updates its section after processing a page to allow resume.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .file_ops import FileOperations


class TypeStateStore:
    """Load/update/save per-type resume state in a JSON file."""

    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file
        self._state: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            self._state = {}
            return
        try:
            self._state = json.loads(self._state_file.read_text(encoding="utf-8"))
            if not isinstance(self._state, dict):
                self._state = {}
        except Exception:
            self._state = {}

    def get(self, type_name: str) -> dict[str, Any]:
        """Get state dict for a type (returns a copy)."""
        value = self._state.get(type_name) or {}
        return dict(value)

    def update(self, type_name: str, mapping: dict[str, Any]) -> None:
        """Shallow-merge state for a type and persist atomically."""
        current = self._state.get(type_name) or {}
        current.update(mapping)
        self._state[type_name] = current
        # Persist
        payload = json.dumps(self._state, ensure_ascii=False, indent=2)
        FileOperations.atomic_write_bytes(self._state_file, payload.encode("utf-8"))
