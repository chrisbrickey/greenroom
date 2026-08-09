"""Translation of TMDB genre payloads into provider-agnostic domain models.

Inbound half of the TMDB anti-corruption layer for the genre endpoints.
"""

from typing import Any

from pydantic import ValidationError

from greenroom.models.genre import Genre, GenreList
from greenroom.services.tmdb.models import TMDBGenre


def to_genre_list(film_data: dict[str, Any], tv_data: dict[str, Any]) -> GenreList:
    """Combine TMDB's separate film and television genre payloads into one list.

    TMDB exposes genres per media type and repeats many names across both, so
    entries are deduplicated by name and flagged with the media types they
    apply to.

    Args:
        film_data: Parsed JSON body from TMDB's film genre endpoint
        tv_data: Parsed JSON body from TMDB's television genre endpoint

    Returns:
        GenreList with Genre objects including media type availability flags
    """

    genres_map: dict[str, Genre] = {}

    for tmdb_genre in _parse_genres(film_data.get("genres", [])):
        genres_map[tmdb_genre.name] = Genre(
            id=tmdb_genre.id,
            name=tmdb_genre.name,
            has_films=True,
            has_tv_shows=False
        )

    for tmdb_genre in _parse_genres(tv_data.get("genres", [])):
        existing = genres_map.get(tmdb_genre.name)
        if existing is not None:
            # Genre already recorded for films, mark as also available for television
            existing.has_tv_shows = True
        else:
            # Television-only genre
            genres_map[tmdb_genre.name] = Genre(
                id=tmdb_genre.id,
                name=tmdb_genre.name,
                has_films=False,
                has_tv_shows=True
            )

    return GenreList(genres=list(genres_map.values()))


def _parse_genres(raw_genres: list[dict[str, Any]]) -> list[TMDBGenre]:
    """Validate raw TMDB genre entries.

    Args:
        raw_genres: Raw genre data from the TMDB API

    Returns:
        List of validated TMDBGenre models (invalid entries are silently skipped)
    """

    valid_genres: list[TMDBGenre] = []
    for genre in raw_genres:
        try:
            valid_genres.append(TMDBGenre(**genre))
        except ValidationError:
            # Skip invalid genre entries
            pass
    return valid_genres
