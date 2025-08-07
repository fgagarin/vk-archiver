"""Downloaders package for VK Photos application."""

from .group import GroupAlbumsDownloader, GroupPhotoDownloader, GroupsPhotoDownloader
from .user import UserPhotoDownloader, UsersPhotoDownloader

__all__ = [
    "GroupAlbumsDownloader",
    "GroupPhotoDownloader",
    "GroupsPhotoDownloader",
    "UserPhotoDownloader",
    "UsersPhotoDownloader",
]
