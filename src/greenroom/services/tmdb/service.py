"""Service layer that encapsulates provider-specific logic."""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import ValidationError

from greenroom.models.media import Media, MediaList
from greenroom.models.genre import Genre, GenreList
from greenroom.models.media_types import MediaType
from greenroom.services.tmdb.client import TMDBClient
from greenroom.services.tmdb.config import TMDB_FILM_CONFIG, TMDB_TELEVISION_CONFIG, TMDBMediaConfig
from greenroom.services.tmdb.models import TMDBGenre


class TMDBService:
    """
    This service encapsulates TMDB-specific logic including
    API communication, response parsing, and data transformation to
    the standard models which are expected by the tools.
    """

    def __init__(self):
        """Initialize the TMDB service."""
        self.client = TMDBClient()
        self.config_map = {
            "film": TMDB_FILM_CONFIG,
            "television": TMDB_TELEVISION_CONFIG
        }

    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        return self.client.SERVICE_NAME

    # =============================================================================
    # Retrieve specific media
    # =============================================================================

    def get_media(
        self,
        media_type: MediaType,
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        max_results: int = 20
    ) -> MediaList:
        """Get media from TMDB.

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
            RuntimeError: For TMDB API errors
            ConnectionError: For network errors
        """
        # Get media type configuration
        config = self.config_map.get(media_type)
        if not config:
            raise ValueError(f"Unsupported media type: {media_type}")

        # Build TMDB query parameters
        params = self._build_params(config, genre_id, year, language, sort_by, page)

        # Call TMDB API
        endpoint = f"/discover/{config.endpoint}"
        data = self.client.get(endpoint, params)

        # Parse and transform response
        tmdb_items = self._parse_response(data["results"], config)
        standard_items = [
            self._to_standard_media(item, config, media_type)
            for item in tmdb_items
        ]

        # Apply max_results limit
        limited_items = standard_items[:max_results]

        # Return standardized response
        return MediaList(
            results=limited_items,
            total_results=data.get("total_results", 0),
            page=page,
            total_pages=data.get("total_pages", 0)
        )

    def _build_params(
        self,
        config: TMDBMediaConfig,
        genre_id: Optional[int],
        year: Optional[int],
        language: Optional[str],
        sort_by: Optional[str],
        page: int
    ) -> dict:
        """Build TMDB-specific query parameters.

        Args:
            config: TMDB media configuration
            genre_id: Optional genre filter
            year: Optional year filter
            language: Optional language filter
            sort_by: Sort order (None defaults to "popularity.desc")
            page: Page number

        Returns:
            Dictionary of TMDB query parameters
        """
        params = {
            "sort_by": sort_by if sort_by is not None else "popularity.desc",
            "page": page,
            "include_adult": False, # Exclude pornographic content
            "include_video": False  # Exclude video-only content
        }

        if genre_id is not None:
            params["with_genres"] = genre_id

        if year is not None:
            params[config.year_param] = year

        if language is not None:
            params["with_original_language"] = language

        return params

    def _parse_response(self, raw_results: list, config: TMDBMediaConfig) -> list:
        """Parse TMDB response using Pydantic models.

        Args:
            raw_results: Raw results array from TMDB API
            config: TMDB media configuration with model class

        Returns:
            List of validated Pydantic model instances
        """
        valid_items = []
        for item_data in raw_results:
            try:
                valid_items.append(config.model_class(**item_data))
            except ValidationError:
                # Skip items that don't match the schema (missing required fields)
                pass
        return valid_items

    def _to_standard_media(
        self,
        tmdb_item,
        config: TMDBMediaConfig,
        media_type: MediaType
    ) -> Media:
        """Transform TMDB model to standard Media model.

        Args:
            tmdb_item: Validated TMDB Pydantic model (TMDBFilm or TMDBTVShow)
            config: TMDB media configuration
            media_type: Type-safe media type

        Returns:
            Standard Media object with normalized field names
        """
        return Media(
            id=str(tmdb_item.id),
            media_type=media_type,
            title=getattr(tmdb_item, config.title_field, None) or "",
            date=self._parse_date(getattr(tmdb_item, config.date_field, None)),
            rating=tmdb_item.vote_average,
            description=tmdb_item.overview,
            genre_ids=tmdb_item.genre_ids or []
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse TMDB date string to date object.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            Date object or None if parsing fails
        """
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None

    # =============================================================================
    # Retrieve categorization information
    # =============================================================================

    def get_genres(self) -> GenreList:
        """Fetch all genres from TMDB for films and TV shows.

        Returns:
            GenreList with standardized Genre objects including media type availability

        Raises:
            RuntimeError: For TMDB API errors
            ConnectionError: For network errors
        """
        # Fetch genres for both films and TV shows
        film_data = self.client.get("/genre/movie/list", {})
        tv_data = self.client.get("/genre/tv/list", {})

        # Parse and validate genre data
        film_genres = self._parse_genres(film_data.get("genres", []))
        tv_genres = self._parse_genres(tv_data.get("genres", []))

        # Combine into unified GenreList
        return self._combine_genre_lists(film_genres, tv_genres)

    def _parse_genres(self, raw_genres: List[Dict[str, Any]]) -> List[TMDBGenre]:
        """Parse TMDB genre response using Pydantic validation.

        Args:
            raw_genres: Raw genre data from TMDB API

        Returns:
            List of validated TMDBGenre models (invalid entries are silently skipped)
        """
        valid_genres = []
        for genre in raw_genres:
            try:
                valid_genres.append(TMDBGenre(**genre))
            except ValidationError:
                # Skip invalid genre entries
                pass
        return valid_genres

    def _combine_genre_lists(
        self,
        film_genres: List[TMDBGenre],
        tv_genres: List[TMDBGenre]
    ) -> GenreList:
        """Combine film and TV genre lists into a unified GenreList.

        Args:
            film_genres: List of validated TMDBGenre models for films
            tv_genres: List of validated TMDBGenre models for TV shows

        Returns:
            GenreList with Genre objects including media type availability flags
        """
        # Build a map by genre name for deduplication
        genres_map: Dict[str, Genre] = {}

        # Add film genres
        for tmdb_genre in film_genres:
            genres_map[tmdb_genre.name] = Genre(
                id=tmdb_genre.id,
                name=tmdb_genre.name,
                has_films=True,
                has_tv_shows=False
            )

        # Add or update with TV genres
        for tmdb_genre in tv_genres:
            if tmdb_genre.name in genres_map:
                # Genre exists for films, mark as also available for TV
                genres_map[tmdb_genre.name].has_tv_shows = True
            else:
                # TV-only genre
                genres_map[tmdb_genre.name] = Genre(
                    id=tmdb_genre.id,
                    name=tmdb_genre.name,
                    has_films=False,
                    has_tv_shows=True
                )

        return GenreList(genres=list(genres_map.values()))
