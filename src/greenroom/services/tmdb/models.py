"""TMDB-specific response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TMDBGenre(BaseModel):
    """TMDB API genre structure.

    Matches the structure returned by TMDB API for genre data.
    """
    id: int
    name: str


class TMDBFilm(BaseModel):
    """TMDB film response structure.

    Matches the structure returned by TMDB API for film data.
    """
    id: int
    title: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: list[int] | None = Field(default_factory=list)

class TMDBTelevision(BaseModel):
    """TMDB television show response structure.

    Matches the structure returned by TMDB API for television data.
    """
    id: int
    name: str | None = None
    first_air_date: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: list[int] | None = Field(default_factory=list)
