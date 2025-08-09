"""Downloaders package for VK Photos application."""

from .chat import (
    ChatMembersPhotoDownloader,
    ChatPhotoDownloader,
    ChatUserPhotoDownloader,
)
from .group import GroupAlbumsDownloader, GroupPhotoDownloader, GroupsPhotoDownloader
from .metadata import MetadataDownloader
from .photos import PhotosDownloader
from .user import UserPhotoDownloader, UsersPhotoDownloader
from .videos import VideosDownloader
from .wall import WallDownloader

__all__ = [
    "ChatMembersPhotoDownloader",
    "ChatPhotoDownloader",
    "ChatUserPhotoDownloader",
    "GroupAlbumsDownloader",
    "GroupPhotoDownloader",
    "GroupsPhotoDownloader",
    "MetadataDownloader",
    "WallDownloader",
    "VideosDownloader",
    "PhotosDownloader",
    "UserPhotoDownloader",
    "UsersPhotoDownloader",
]
