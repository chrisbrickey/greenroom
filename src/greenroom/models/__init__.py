"""Standard data models for media representation."""

from greenroom.models.media import Media, MediaList
from greenroom.models.genre import Genre, GenreList
from greenroom.models.media_types import (
    MediaType,
    MEDIA_TYPE_FILM,
    MEDIA_TYPE_TELEVISION,
    MEDIA_TYPE_PODCAST,
    MEDIA_TYPE_BOOK,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_GAME,
)
from greenroom.models.responses import (
    DiscoveryResultDict,
    GenrePropertiesDict,
    LLMComparisonResultDict,
    LLMResponseEntryDict,
    MediaResultDict,
)

__all__ = [
    "Media",
    "MediaList",
    "Genre",
    "GenreList",
    "MediaType",
    "MEDIA_TYPE_FILM",
    "MEDIA_TYPE_TELEVISION",
    "MEDIA_TYPE_PODCAST",
    "MEDIA_TYPE_BOOK",
    "MEDIA_TYPE_MUSIC",
    "MEDIA_TYPE_GAME",
    "DiscoveryResultDict",
    "GenrePropertiesDict",
    "LLMComparisonResultDict",
    "LLMResponseEntryDict",
    "MediaResultDict",
]
