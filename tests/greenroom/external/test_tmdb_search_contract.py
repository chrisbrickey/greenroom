"""Contract tests for the search-by-title parameters the tools send to TMDB.

Run with: uv run pytest -m external
"""

from datetime import date

import pytest

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService

pytestmark = pytest.mark.external

# Both media types are exercised because TMDB names the search year parameter
# differently per endpoint (see TMDBMediaConfig.year_param)
MEDIA_TYPES = (MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION)

# A common word rather than a specific real title, franchise, or brand: broad
# enough that the live catalog is virtually certain to contain matches for
# either media type, and to span more than one page of results.
BROAD_MATCH_QUERY = "man"

# Obviously fake, used to pin down how the provider treats a query nothing in
# its catalog could ever match
NO_MATCH_QUERY = "not-a-real-title-000"

# Far enough back that the provider's catalog for that year has settled
YEARS_BEFORE_PRESENT = 2

# ISO 639-1 code used to confirm display_language actually changes returned text
SAMPLE_DISPLAY_LANGUAGE = "es"

FIRST_PAGE = 1
SECOND_PAGE = 2

# Deliberately larger than the page we expect, so our own truncation cannot hide
# a page that grew. The service does not validate max_results; the tool layer
# does, and these tests sit below it.
BEYOND_PAGE_SIZE = PROVIDER_PAGE_SIZE * 5


def titles_in_returned_order(media_list: MediaList) -> list[str]:
    """Titles in the order the provider returned the entries."""
    return [item.title for item in media_list.results]


def media_ids_in_returned_order(media_list: MediaList) -> list[str]:
    """Ids in the order the provider returned them."""
    return [item.id for item in media_list.results]


def item_with_id(media_list: MediaList, media_id: str) -> Media:
    """The single entry in a MediaList with the given id."""
    matches = [item for item in media_list.results if item.id == media_id]
    assert matches, f"id {media_id} missing from results"
    return matches[0]


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
    result = await tmdb_service.search_media(media_type=media_type, query=BROAD_MATCH_QUERY)

    titles = titles_in_returned_order(result)
    assert titles, "expected at least one match for a broad query term"
    assert BROAD_MATCH_QUERY in titles[0].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_year_filter_narrows_results_to_that_year(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """The year filter constrains results, under whichever parameter name the
    provider's search endpoint uses for this media type."""
    requested_year = date.today().year - YEARS_BEFORE_PRESENT

    result = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, year=requested_year
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

    This is a stronger claim than the discover tools' original-language
    filter, which only needs to be accepted (see test_provider_accepts_the_
    original_language_filter in test_tmdb_discover_contract.py). Search's
    display_language is documented as controlling the language of the text
    TMDB sends back, so this asserts the text itself changes, matched by id
    so a difference in ordering between languages cannot hide the check.
    """
    default = await tmdb_service.search_media(media_type=media_type, query=BROAD_MATCH_QUERY)
    translated = await tmdb_service.search_media(
        media_type=media_type,
        query=BROAD_MATCH_QUERY,
        display_language=SAMPLE_DISPLAY_LANGUAGE
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
    """A query nothing in the catalog matches comes back as an empty result set.

    The tools rely on this: if the provider ever raised for "no matches"
    instead of returning an empty page, that would surface to callers as an
    unhandled error rather than a normal, empty response.
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

    MAX_RESULTS_MAX is defined as that number, so the ceiling the tools
    advertise is only honest while this holds. Were the provider to serve a
    smaller page, max_results at the ceiling would quietly under-deliver; a
    larger page, and we would discard results already paid for.
    """
    result = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, max_results=BEYOND_PAGE_SIZE
    )

    assert result.total_pages > FIRST_PAGE, "need a query whose matches exceed one page"
    assert len(result.results) == PROVIDER_PAGE_SIZE


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_consecutive_pages_return_different_media(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """Pagination advances through the search results rather than repeating a page."""
    first = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, page=FIRST_PAGE
    )
    second = await tmdb_service.search_media(
        media_type=media_type, query=BROAD_MATCH_QUERY, page=SECOND_PAGE
    )

    first_ids = {item.id for item in first.results}
    second_ids = {item.id for item in second.results}

    assert first_ids and second_ids
    assert not first_ids & second_ids
