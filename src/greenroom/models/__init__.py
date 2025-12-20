"""Standard data models for media representation."""

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import (
    MediaType,
    MEDIA_TYPE_FILM,
    MEDIA_TYPE_TELEVISION,
    MEDIA_TYPE_PODCAST,
    MEDIA_TYPE_BOOK,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_GAME,
)

__all__ = [
    "Media",
    "MediaList",
    "MediaType",
    "MEDIA_TYPE_FILM",
    "MEDIA_TYPE_TELEVISION",
    "MEDIA_TYPE_PODCAST",
    "MEDIA_TYPE_BOOK",
    "MEDIA_TYPE_MUSIC",
    "MEDIA_TYPE_GAME",
]
