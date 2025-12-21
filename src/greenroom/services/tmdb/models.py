"""TMDB-specific response models."""

from pydantic import BaseModel, Field
from typing import Optional, List


class TMDBFilm(BaseModel):
    """TMDB film response structure.

    Matches the structure returned by TMDB API for film data.
    """
    id: int
    title: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    overview: Optional[str] = None
    genre_ids: Optional[List[int]] = Field(default_factory=list)

class TMDBTelevision(BaseModel):
    """TMDB television show response structure.

    Matches the structure returned by TMDB API for television data.
    """
    id: int
    name: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: Optional[float] = None
    overview: Optional[str] = None
    genre_ids: Optional[List[int]] = Field(default_factory=list)
