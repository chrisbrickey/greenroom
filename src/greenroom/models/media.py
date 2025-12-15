"""Provider-agnostic media data models."""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date


@dataclass
class Media:
    """Standard media representation, provider-agnostic.

    This model provides a normalized interface for media data from any provider
    (TMDB, IMDb, OMDb, etc.), ensuring consistent field names and data types.
    """
    id: str                                 # Generic ID (could be int/string depending on provider)
    media_type: str                         # "film", "tv", etc.
    title: str                              # Normalized title field
    date: Optional[date] = None             # Normalized date field (release/air date)
    rating: Optional[float] = None          # Normalized rating (0-10 scale)
    description: Optional[str] = None       # Overview/synopsis
    genre_ids: List[int] = field(default_factory=list)  # List of genre IDs


@dataclass
class MediaList:
    """Standard paginated media list response.

    Represents a page of media results with pagination metadata.
    """
    results: List[Media]
    total_results: int
    page: int
    total_pages: int
