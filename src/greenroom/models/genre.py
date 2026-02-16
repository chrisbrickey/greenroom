"""Provider-agnostic genre data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Genre:
    """Standard genre representation, provider-agnostic.

    This model provides a normalized interface for genre data from any provider
    (TMDB, IMDb, OMDb, etc.), ensuring consistent field names and data types.
    """
    id: int
    name: str
    has_films: bool = False
    has_tv_shows: bool = False


@dataclass
class GenreList:
    """Standard genre list response.

    Represents a collection of genres with media type availability.
    """
    genres: list[Genre] = field(default_factory=list)
