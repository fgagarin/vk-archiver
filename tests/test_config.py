"""Tests for configuration management utilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from vk_photos.utils.config import ConfigManager

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_config_manager_loads_yaml(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """It should load YAML config into a dictionary."""
    # Ensure no environment override is present
    monkeypatch.delenv("VK_TOKEN", raising=False)

    cfg_file = tmp_path / "config.yaml"
    _write_yaml(
        cfg_file,
        """
    token: "secret"
    extra: 123
    """,
    )

    cfg = ConfigManager(cfg_file)

    data = cfg.get_config()
    assert isinstance(data, dict)
    assert data.get("token") == "secret"
    assert data.get("extra") == 123


def test_validate_config_forbids_login_password(tmp_path: Path) -> None:
    """It should raise when login/password are present in config."""
    cfg_file = tmp_path / "config.yaml"
    _write_yaml(
        cfg_file,
        """
    token: "secret"
    login: "user"
    password: "pass"
    """,
    )

    cfg = ConfigManager(cfg_file)

    with pytest.raises(RuntimeError):
        cfg.validate_config()


def test_env_token_overrides_yaml_token(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """It should prefer VK_TOKEN from environment over YAML token when present."""
    cfg_file = tmp_path / "config.yaml"
    _write_yaml(
        cfg_file,
        """
    token: "yaml_secret"
    """,
    )

    monkeypatch.setenv("VK_TOKEN", "env_secret")

    cfg = ConfigManager(cfg_file)
    data = cfg.get_config()
    assert data.get("token") == "env_secret"
