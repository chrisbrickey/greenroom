"""Media discovery tools for the greenroom MCP server."""

from typing import Dict, Any, Optional
from fastmcp import FastMCP

from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media import MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register media discovery tools with the MCP server."""

    # Initialize service (could be dependency injected in the future)
    media_service = TMDBService()

    @mcp.tool()
    def discover_films(
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Discovers films from based on optional filters like genre, release year,
        language, and sorting preferences. For now, defaults to TMDB service.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional release year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (None defaults to "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": str,
                        "media_type": str,
                        "title": str,
                        "date": str (YYYY-MM-DD format, may be None),
                        "rating": float (0-10 scale, may be None),
                        "description": str (may be None),
                        "genre_ids": List[int]
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int,
                "provider": str
            }

        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If service returns an error
            ConnectionError: If unable to connect to service
        """
        # Validate parameters
        _validate_discovery_params_internal(MEDIA_TYPE_FILM, year, page, max_results, language, sort_by)

        # Call service
        media_list = media_service.discover(
            media_type=MEDIA_TYPE_FILM,
            genre_id=genre_id,
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            max_results=max_results
        )

        # Format for agent
        return _format_media_list(media_list, media_service)

    @mcp.tool()
    def discover_television(
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Discovers television shows based on optional filters like genre, first air year,
        language, and sorting preferences. For now, defaults to TMDB service.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional first air year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (None defaults to "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": str,
                        "media_type": str,
                        "title": str,
                        "date": str (YYYY-MM-DD format, may be None),
                        "rating": float (0-10 scale, may be None),
                        "description": str (may be None),
                        "genre_ids": List[int]
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int,
                "provider": str
            }

        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If service returns an error
            ConnectionError: If unable to connect to service
        """
        # Validate parameters
        _validate_discovery_params_internal(MEDIA_TYPE_TELEVISION, year, page, max_results, language, sort_by)

        # Call service
        media_list = media_service.discover(
            media_type=MEDIA_TYPE_TELEVISION,
            genre_id=genre_id,
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            max_results=max_results
        )

        # Format for agent
        return _format_media_list(media_list, media_service)


def _validate_discovery_params_internal(
    media_type: str,
    year: Optional[int],
    page: int,
    max_results: int,
    language: Optional[str],
    sort_by: Optional[str]
) -> None:
    """Validate discovery parameters (internal version).

    Args:
        media_type: Type of media
        year: Optional year filter
        page: Page number
        max_results: Maximum results
        language: Optional language code
        sort_by: Sort order

    Raises:
        ValueError: If any parameter is invalid
    """
    if media_type not in [MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION]:
        raise ValueError(f"media_type must be one of: {MEDIA_TYPE_FILM}, {MEDIA_TYPE_TELEVISION}")

    if year is not None and year < 1900:
        raise ValueError("year must be 1900 or later")

    if page < 1:
        raise ValueError("page must be 1 or greater")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")

    if language is not None:
        if not isinstance(language, str) or len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')")

    if sort_by is not None:
        valid_sort_options = [
            "popularity.desc", "popularity.asc",
            "vote_average.desc", "vote_average.asc",
            "date.desc", "date.asc"
        ]
        if sort_by not in valid_sort_options:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")


def _format_media_list(media_list: MediaList, media_service: TMDBService) -> Dict[str, Any]:
    """Format MediaList for agent consumption.

    Args:
        media_list: MediaList from service
        media_service: Media service instance for getting provider name

    Returns:
        Dictionary formatted for agent
    """
    return {
        "results": [
            {
                "id": media.id,
                "media_type": media.media_type,
                "title": media.title,
                "date": media.date.isoformat() if media.date else None,
                "rating": media.rating,
                "description": media.description,
                "genre_ids": media.genre_ids
            }
            for media in media_list.results
        ],
        "total_results": media_list.total_results,
        "page": media_list.page,
        "total_pages": media_list.total_pages,
        "provider": media_service.get_provider_name()
    }
