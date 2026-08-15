"""Filter-by-criteria media tools for the greenroom MCP server.

These tools browse by criteria such as genre or year.
See search_tools for looking up a specific title the user named.
"""

from fastmcp import FastMCP

from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION, MediaType
from greenroom.models.responses import DiscoveryResultDict
from greenroom.services.media_limits import DISCOVER_MAX_RESULTS
from greenroom.services.protocols import MediaService
from greenroom.tools.discovery.formatting import format_media_list
from greenroom.tools.discovery.validation import validate_discovery_params


def register_discovery_tools(mcp: FastMCP, service: MediaService) -> None:
    """Register discovery tools with the MCP server.

    Args:
        mcp: Server to register the tools with
        service: Media provider the registered tools delegate to
    """

# -------------
# Registration
# -------------

    @mcp.tool()
    async def discover_films(
        genre_id: int | None = None,
        year: int | None = None,
        original_language: str | None = None,
        sort_by: str | None = None,
        page: int = 1,
        max_results: int = DISCOVER_MAX_RESULTS
    ) -> DiscoveryResultDict:
        """
        Retrieve a list of films based on optional filters like genre, release year,
        original language, and sorting preferences. For now, defaults to TMDB service.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional release year to filter by (e.g., 2024)
            original_language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
                               that filters the catalog down to films produced in that
                               language. This does not translate the returned text.
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (None defaults to "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return from this page

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
            APIResponseError: If service returns an error
            APIConnectionError: If unable to connect to service
        """

        # Delegate to public orchestration method to enable unit testing without FastMCP server setup
        return await fetch_films(service, genre_id, year, original_language, sort_by, page, max_results)

    @mcp.tool()
    async def discover_television(
        genre_id: int | None = None,
        year: int | None = None,
        original_language: str | None = None,
        sort_by: str | None = None,
        page: int = 1,
        max_results: int = DISCOVER_MAX_RESULTS
    ) -> DiscoveryResultDict:
        """
        Retrieve a list of television shows based on optional filters like genre, first air year,
        original language, and sorting preferences. For now, defaults to TMDB service.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional first air year to filter by (e.g., 2024)
            original_language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
                               that filters the catalog down to shows produced in that
                               language. This does not translate the returned text.
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (None defaults to "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return from this page

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
            APIResponseError: If service returns an error
            APIConnectionError: If unable to connect to service
        """

        # Delegate to public orchestration method to enable unit testing without FastMCP server setup
        return await fetch_television(service, genre_id, year, original_language, sort_by, page, max_results)

# -------------
# Orchestration
# -------------

async def fetch_films(
    media_service: MediaService,
    genre_id: int | None = None,
    year: int | None = None,
    original_language: str | None = None,
    sort_by: str | None = None,
    page: int = 1,
    max_results: int = DISCOVER_MAX_RESULTS,
) -> DiscoveryResultDict:
    return await _discover_media(
        media_service, MEDIA_TYPE_FILM, genre_id, year, original_language, sort_by, page, max_results
    )

async def fetch_television(
    media_service: MediaService,
    genre_id: int | None = None,
    year: int | None = None,
    original_language: str | None = None,
    sort_by: str | None = None,
    page: int = 1,
    max_results: int = DISCOVER_MAX_RESULTS
) -> DiscoveryResultDict:
    return await _discover_media(
        media_service, MEDIA_TYPE_TELEVISION, genre_id, year, original_language, sort_by, page, max_results
    )

async def _discover_media(
    media_service: MediaService,
    media_type: MediaType,
    genre_id: int | None,
    year: int | None,
    original_language: str | None,
    sort_by: str | None,
    page: int,
    max_results: int,
) -> DiscoveryResultDict:

    # Validate parameters
    validate_discovery_params(
        year=year,
        page=page,
        max_results=max_results,
        original_language=original_language,
        sort_by=sort_by
    )

    # Call service
    media_list = await media_service.get_media(
        media_type=media_type,
        genre_id=genre_id,
        year=year,
        original_language=original_language,
        sort_by=sort_by,
        page=page,
        max_results=max_results
    )

    # Format for agent
    return format_media_list(media_list, media_service)
