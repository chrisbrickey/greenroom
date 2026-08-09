"""TMDB-specific response models."""

from pydantic import BaseModel, Field


class TMDBGenre(BaseModel):
    """TMDB API genre structure.

    Matches the structure returned by TMDB API for genre data.
    """
    id: int
    name: str


class TMDBMediaItem(BaseModel):
    """Fields TMDB returns for every media item, whatever the media type.

    Media-type-specific subclasses add the title and date fields, which TMDB
    names differently per type. TMDBMediaConfig records those names so the
    mapper can read them without knowing which subclass it holds.
    """
    id: int
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: list[int] | None = Field(default_factory=list)


class TMDBFilm(TMDBMediaItem):
    """TMDB film response structure.

    Matches the structure returned by TMDB API for film data.
    """
    title: str | None = None
    release_date: str | None = None


class TMDBTelevision(TMDBMediaItem):
    """TMDB television show response structure.

    Matches the structure returned by TMDB API for television data.
    """
    name: str | None = None
    first_air_date: str | None = None
