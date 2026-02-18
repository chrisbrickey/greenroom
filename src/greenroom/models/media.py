"""Provider-agnostic media data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from greenroom.models.media_types import MediaType


@dataclass
class Media:
    """Standard media representation, provider-agnostic.

    This model provides a normalized interface for media data from any provider
    (TMDB, IMDb, OMDb, etc.), ensuring consistent field names and data types.
    """
    id: str                                 # Generic ID (could be int/string depending on provider)
    media_type: MediaType                   # Type-safe media type
    title: str                              # Normalized title field
    date: date | None = None             # Normalized date field (release/air date)
    rating: float | None = None          # Normalized rating (0-10 scale)
    description: str | None = None       # Overview/synopsis
    genre_ids: list[int] | None = None   # List of genre IDs


@dataclass
class MediaList:
    """Standard paginated media list response.

    Represents a page of media results with pagination metadata.
    """
    results: list[Media]
    total_results: int
    page: int
    total_pages: int
