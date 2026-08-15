"""Tests on the API contract with TMDB for search-by-title concerns.

Run with: uv run pytest -m external
"""

from datetime import date

import pytest

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService

from .conftest import MAX_BOUNDARY_OVERLAP, media_ids_in_returned_order

pytestmark = pytest.mark.external

#------------
# Fixtures
#------------

# TMDB uses different parameter names for films and TV, so every test runs both.
MEDIA_TYPES = (MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION)

# A common english word (not a real title) with high probability of returning more than one page of results
BROAD_MATCH_QUERY = "the"

# Obviously fake. Used to pin down how the provider treats a query that won't match anything in its catalog
NO_MATCH_QUERY = "not-a-real-title-000"

#------------
# Helpers
#------------

def titles_in_returned_order(media_list: MediaList) -> list[str]:
    """Titles in the order the provider returned the entries."""
    return [item.title for item in media_list.results]


def item_with_id(media_list: MediaList, media_id: str) -> Media:
    """The single entry in a MediaList with the given id."""
    matches = [item for item in media_list.results if item.id == media_id]
    assert matches, f"id {media_id} missing from results"
    return matches[0]

#------------
# Tests
#------------

@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_top_result_title_matches_the_query(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """The provider's relevance ranking puts a matching title first.

    This is the ordering the tools promise callers ("results ordered by
    relevance to the query"). The query term is chosen to appear in many
    catalog titles, so a change in how the provider ranks matches would be
    caught here rather than surfacing as a confusing result for a real query.
    """
    result = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, max_results=PROVIDER_PAGE_SIZE
    )

    titles = titles_in_returned_order(result)
    assert titles, "expected at least one match for a broad query term"
    assert BROAD_MATCH_QUERY in titles[0].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_year_filter_narrows_results_to_that_year(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """Filtering by year returns only media from that year."""
    requested_year = date.today().year - 2 # two years ago
    result = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, year=requested_year,
        max_results=PROVIDER_PAGE_SIZE
    )

    assert result.results
    for item in result.results:
        if item.date is not None:
            assert item.date.year == requested_year


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_display_language_changes_the_returned_text(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """display_language actually translates the returned title/description.

    This asserts that the language of the text itself changes. Items are matched
    by id so a difference in ordering between languages cannot hide the check.
    """
    default = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, max_results=PROVIDER_PAGE_SIZE
    )
    translated = await tmdb_service.search_media(
        media_type=media_type,
        query=BROAD_MATCH_QUERY,
        display_language="es", # spanish
        max_results=PROVIDER_PAGE_SIZE
    )

    assert default.results and translated.results
    top_id = default.results[0].id
    default_item = item_with_id(default, top_id)
    translated_item = item_with_id(translated, top_id)

    assert (
        default_item.title != translated_item.title
        or default_item.description != translated_item.description
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_query_with_no_matches_returns_empty_results_not_an_error(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """A query that doesn't match anything in the provider's catalog returns empty result set.

    This confirms that the provider does not return an error when there is no match.
    If an error is ever returned, then greenroom needs to be adjusted to handle such an error gracefully.
    """
    result = await tmdb_service.search_media(media_type=media_type, query=NO_MATCH_QUERY)

    assert result.results == []


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_a_full_search_page_holds_the_result_count_we_assume(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """A full page holds exactly PROVIDER_PAGE_SIZE results.

    This value is relevant upstream for bounding parameters like max_results.
    """
    endpoint = f"/search/{tmdb_service.config_map[media_type].endpoint}"
    payload = await tmdb_service.client.get(endpoint, {"query": BROAD_MATCH_QUERY})

    assert payload["total_pages"] > 1, "need a query whose matches exceed one page"
    assert len(payload["results"]) == PROVIDER_PAGE_SIZE


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_consecutive_pages_return_different_media(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """Pagination advances through the search results rather than repeating a page."""
    first = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, page=1, max_results=PROVIDER_PAGE_SIZE
    )
    second = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, page=2, max_results=PROVIDER_PAGE_SIZE
    )

    first_ids = set(media_ids_in_returned_order(first))
    second_ids = set(media_ids_in_returned_order(second))

    assert first_ids and second_ids
    assert len(second_ids - first_ids) >= PROVIDER_PAGE_SIZE - MAX_BOUNDARY_OVERLAP
