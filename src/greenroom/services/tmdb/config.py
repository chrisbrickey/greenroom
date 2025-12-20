"""TMDB-specific configuration for media types."""

from dataclasses import dataclass
from typing import Type
from pydantic import BaseModel


@dataclass
class TMDBMediaConfig:
    """TMDB-specific configuration for a media type.

    Encapsulates all the TMDB-specific naming and parameter differences
    between different media types (films vs TV shows).
    """
    endpoint: str                 # API endpoint: "movie" or "tv"
    year_param: str               # Year parameter name: "primary_release_year" or "first_air_date_year"
    title_field: str              # Response title field: "title" or "name"
    date_field: str               # Response date field: "release_date" or "first_air_date"
    date_sort_prefix: str         # Sort parameter prefix: "release_date" or "first_air_date"
    model_class: Type[BaseModel]  # Pydantic model for validation: TMDBFilm or TMDBTVShow


# Import models here to avoid circular import
from greenroom.services.tmdb.models import TMDBFilm, TMDBTelevision


TMDB_FILM_CONFIG = TMDBMediaConfig(
    endpoint="movie",
    year_param="primary_release_year",
    title_field="title",
    date_field="release_date",
    date_sort_prefix="release_date",
    model_class=TMDBFilm
)


TMDB_TELEVISION_CONFIG = TMDBMediaConfig(
    endpoint="tv",
    year_param="first_air_date_year",
    title_field="name",
    date_field="first_air_date",
    date_sort_prefix="first_air_date",
    model_class=TMDBTelevision
)
