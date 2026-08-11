"""Service layer that encapsulates provider-specific logic."""

import asyncio

from greenroom.models.genre import GenreList
from greenroom.models.media import MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION, MediaType
from greenroom.services.tmdb.client import TMDBClient
from greenroom.services.tmdb.config import TMDB_FILM_CONFIG, TMDB_TELEVISION_CONFIG, TMDBMediaConfig
from greenroom.services.tmdb.genre_mapper import to_genre_list
from greenroom.services.tmdb.media_mapper import to_media_list
from greenroom.services.tmdb.params import build_discover_params


# Genre endpoints are fixed per media type rather than configurable, because
# TMDB returns genre lists in a single shape that is not media-type dependent.
FILM_GENRES_ENDPOINT = "/genre/movie/list"
TELEVISION_GENRES_ENDPOINT = "/genre/tv/list"


class TMDBService:
    """
    This service encapsulates TMDB-specific logic including
    API communication, response parsing, and data transformation to
    the standard models which are expected by the tools.

    The translation between TMDB's vocabulary and the standard models lives in
    sibling modules: params builds outgoing requests, and media_mapper and
    genre_mapper convert incoming payloads. This class orchestrates them.
    """

    def __init__(self) -> None:
        """Initialize the TMDB service."""
        self.client = TMDBClient()
        self.config_map: dict[str, TMDBMediaConfig] = {
            MEDIA_TYPE_FILM: TMDB_FILM_CONFIG,
            MEDIA_TYPE_TELEVISION: TMDB_TELEVISION_CONFIG
        }

    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        return self.client.SERVICE_NAME

    # =============================================================================
    # Retrieve media
    # =============================================================================

    async def get_media(
        self,
        media_type: MediaType,
        genre_id: int | None = None,
        year: int | None = None,
        language: str | None = None,
        sort_by: str | None = None,
        page: int = 1,
        max_results: int = 20
    ) -> MediaList:
        """From TMDB, retrieve list of media matching the given criteria.

        Args:
            media_type: Type-safe media type (see media_types module)
            genre_id: Optional TMDB genre ID filter
            year: Optional year filter (release/air year)
            language: Optional ISO 639-1 language code
            sort_by: Sort order (None defaults to "popularity.desc")
            page: Page number (1-indexed)
            max_results: Maximum results to return

        Returns:
            MediaList with standardized Media objects

        Raises:
            ValueError: If media_type is not supported
            APIResponseError: For TMDB API errors
            APIConnectionError: For network errors
        """

        config = self._config_for(media_type)
        params = build_discover_params(config, genre_id, year, language, sort_by, page)
        data = await self.client.get(f"/discover/{config.endpoint}", params)

        return to_media_list(data, config, media_type, page, max_results)

    def _config_for(self, media_type: MediaType) -> TMDBMediaConfig:
        """Look up the TMDB configuration for a media type.

        Args:
            media_type: Type-safe media type

        Returns:
            TMDB media configuration for that type

        Raises:
            ValueError: If this provider does not support the media type
        """

        config = self.config_map.get(media_type)
        if not config:
            raise ValueError(f"Unsupported media type: {media_type}")
        return config

    # =============================================================================
    # Retrieve categorization information
    # =============================================================================

    async def get_genres(self) -> GenreList:
        """Fetch all genres from TMDB for films and TV shows.

        Returns:
            GenreList with standardized Genre objects including media type availability

        Raises:
            APIResponseError: For TMDB API errors
            APIConnectionError: For network errors
        """

        # Concurrently fetch genres for films and television
        film_data, tv_data = await asyncio.gather(
            self.client.get(FILM_GENRES_ENDPOINT, {}),
            self.client.get(TELEVISION_GENRES_ENDPOINT, {})
        )

        return to_genre_list(film_data, tv_data)
