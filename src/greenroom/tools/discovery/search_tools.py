"""Look-up-by-title media tools for the greenroom MCP server.

These tools find a specific title the user named. See discover_tools for
browsing by criteria such as genre or year.
"""

from fastmcp import FastMCP

from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION, MediaType
from greenroom.models.responses import DiscoveryResultDict
from greenroom.services.media_limits import SEARCH_MAX_RESULTS
from greenroom.services.protocols import MediaService
from greenroom.tools.discovery.formatting import format_media_list
from greenroom.tools.discovery.validation import validate_search_params


def register_search_tools(mcp: FastMCP, service: MediaService) -> None:
    """Register the look-up-by-title media tools with the MCP server.

    Args:
        mcp: Server to register the tools with
        service: Media provider the registered tools delegate to
    """

    @mcp.tool()
    async def search_films(
        query: str,
        year: int | None = None,
        display_language: str | None = None,
        page: int = 1,
        max_results: int = SEARCH_MAX_RESULTS
    ) -> DiscoveryResultDict:
        """
        Looks up films by title. Use this when the user provides the title of a specific film.
        Use discover_films instead when browsing by criteria like genre or year.

        For now, defaults to TMDB service.

        Args:
            query: Film title to search for (required, e.g., "The Matrix")
            year: Optional release year to narrow the search by (e.g., 2024)
            display_language: Optional ISO 639-1 language code (e.g., "fr")
                              that specifies whether to translate the returned
                              title and description into a different display language.
                              This is not a filter on the film's original language.
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return from this page
                         (default: SEARCH_MAX_RESULTS, max: MAX_RESULTS_MAX).
                         One call fetches one page, so use page to reach
                         results beyond that.

        Returns:
            Dictionary containing (results ordered by relevance to the query):
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

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await find_films(service, query, year, display_language, page, max_results)

    @mcp.tool()
    async def search_television(
        query: str,
        year: int | None = None,
        display_language: str | None = None,
        page: int = 1,
        max_results: int = SEARCH_MAX_RESULTS
    ) -> DiscoveryResultDict:
        """
        Looks up television shows by title. Use this when the user provides the title of a specific show.
        Use discover_television instead when browsing by criteria like genre or year.

        For now, defaults to TMDB service.

        Args:
            query: Television show title to search for (required, e.g., "Severance")
            year: Optional first air year to narrow the search by (e.g., 2024)
            display_language: Optional ISO 639-1 language code (e.g., "fr")
                              that specifies whether to translate the returned
                              title and description into a different display language.
                              This is not a filter on the film's original language.
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return from this page
                         (default: SEARCH_MAX_RESULTS, max: MAX_RESULTS_MAX).
                         One call fetches one page, so use page to reach
                         results beyond that.

        Returns:
            Dictionary containing (results ordered by relevance to the query):
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

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await find_television(service, query, year, display_language, page, max_results)


# =============================================================================
# Search flow (find media by title)
#
# find_films/find_television are the public, independently-testable seams
# (extracted from tools to ease unit testing); both share the same
# validate -> call service -> format shape via _search_media.
# =============================================================================

async def find_films(
    media_service: MediaService,
    query: str,
    year: int | None = None,
    display_language: str | None = None,
    page: int = 1,
    max_results: int = SEARCH_MAX_RESULTS
) -> DiscoveryResultDict:
    return await _search_media(
        media_service, MEDIA_TYPE_FILM, query, year, display_language, page, max_results
    )

async def find_television(
    media_service: MediaService,
    query: str,
    year: int | None = None,
    display_language: str | None = None,
    page: int = 1,
    max_results: int = SEARCH_MAX_RESULTS
) -> DiscoveryResultDict:
    return await _search_media(
        media_service, MEDIA_TYPE_TELEVISION, query, year, display_language, page, max_results
    )

async def _search_media(
    media_service: MediaService,
    media_type: MediaType,
    query: str,
    year: int | None,
    display_language: str | None,
    page: int,
    max_results: int,
) -> DiscoveryResultDict:

    # Validate parameters
    validate_search_params(
        query=query, year=year, page=page, max_results=max_results,
        display_language=display_language
    )

    # Call service
    media_list = await media_service.search_media(
        media_type=media_type,
        query=query,
        year=year,
        display_language=display_language,
        page=page,
        max_results=max_results
    )

    # Format for agent
    return format_media_list(media_list, media_service)
