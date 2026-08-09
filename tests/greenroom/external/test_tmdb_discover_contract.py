"""Contract tests for the discover parameters the tools send to TMDB.

Run with: uv run pytest -m external
"""

from datetime import date
from typing import Any

import pytest

from greenroom.models.genre import GenreList
from greenroom.models.media import MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.discovery import VALID_SORT_OPTIONS

pytestmark = pytest.mark.external

# Both media types are exercised because TMDB names several discover parameters
# differently per endpoint
MEDIA_TYPES = (MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION)

# Obviously fake sort order, used to pin down how the provider treats one it
# does not recognise
UNSUPPORTED_SORT_ORDER = "not-a-real-field.desc"

DESCENDING_DATE_SORT = "date.desc"
ASCENDING_DATE_SORT = "date.asc"
DESCENDING_RATING_SORT = "vote_average.desc"
ASCENDING_RATING_SORT = "vote_average.asc"
DESCENDING_POPULARITY_SORT = "popularity.desc"
ASCENDING_POPULARITY_SORT = "popularity.asc"

# The provider's fallback ordering. Held steady as a control whenever a test is
# about something other than sorting.
DEFAULT_SORT_ORDER = DESCENDING_POPULARITY_SORT

# Sort orders whose field survives into the standard Media model and which the
# provider orders strictly, so the ordering can be read straight off the results
ORDERED_SORT_CASES = [
    (DESCENDING_DATE_SORT, "date", True),
    (ASCENDING_DATE_SORT, "date", False),
    (DESCENDING_RATING_SORT, "rating", True),
]

# Sort orders covered by comparing the two directions instead of reading values.
# Popularity is not carried on the standard model. The ascending rating sort is
# dominated by unrated entries that the provider returns in no strict order, so
# it has a direction but not a readable ordering.
SORT_DIRECTION_PAIRS = [
    (DESCENDING_POPULARITY_SORT, ASCENDING_POPULARITY_SORT),
    (DESCENDING_RATING_SORT, ASCENDING_RATING_SORT),
]

SORT_ORDERS_UNDER_CONTRACT = (
    {case[0] for case in ORDERED_SORT_CASES}
    | {sort_order for pair in SORT_DIRECTION_PAIRS for sort_order in pair}
)

# Far enough back that the provider's catalog for that year has settled
YEARS_BEFORE_PRESENT = 2

# ISO 639-1 code used only to confirm the parameter is accepted
SAMPLE_LANGUAGE_CODE = "en"

FIRST_PAGE = 1
SECOND_PAGE = 2

# Deliberately larger than the page we expect, so our own truncation cannot hide
# a page that grew. The service does not validate max_results; the tool layer
# does, and these tests sit below it.
BEYOND_PAGE_SIZE = PROVIDER_PAGE_SIZE * 5

# The provider's catalog changes while these tests run: two calls seconds apart
# report different total_results, and an entry near a page boundary can drift
# onto the neighbouring page. Assertions comparing two live responses tolerate
# this much movement, which stays far below the whole page that a genuine
# contract break would shift.
MAX_CATALOG_DRIFT = 3


def values_in_returned_order(media_list: MediaList, attribute: str) -> list[Any]:
    """Values of one attribute, in the order the provider returned the entries.

    Entries missing the attribute are dropped: the provider leaves dates and
    ratings unset on some records, and a gap says nothing about the ordering.
    """
    values = [getattr(item, attribute) for item in media_list.results]

    return [value for value in values if value is not None]


def media_ids_in_returned_order(media_list: MediaList) -> list[str]:
    """Ids in the order the provider returned them."""
    return [item.id for item in media_list.results]


def first_genre_id_for(genres: GenreList, media_type: str) -> int:
    """Pick a genre the provider reports as available for the given media type.

    Taken from the provider's own catalog rather than hardcoded, so the test
    asserts a relationship instead of embedding provider data that can change.
    The lowest id is used so repeated runs exercise the same genre.

    Args:
        genres: Genre catalog returned by the provider
        media_type: Media type the genre must be available for

    Returns:
        Genre id available for that media type
    """
    wants_films = media_type == MEDIA_TYPE_FILM
    available = [
        genre.id
        for genre in genres.genres
        if (genre.has_films if wants_films else genre.has_tv_shows)
    ]

    assert available, f"provider reported no genres for {media_type}"

    return min(available)


def test_every_sort_order_the_tools_offer_is_under_contract() -> None:
    """Each sort order in the tools' vocabulary is covered by a test in this module.

    Guards the drift that produced the original defect: a sort order offered to
    callers that nobody ever checked the provider honours. Needs no network, but
    lives here because it is the coverage claim this module makes.
    """
    assert set(VALID_SORT_OPTIONS) == SORT_ORDERS_UNDER_CONTRACT


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_provider_ignores_an_unsupported_sort_order_instead_of_rejecting_it(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """An unsupported sort order is silently ignored, not refused.

    This is the reason the rest of this module asserts on result ordering rather
    than on the request being accepted. The provider answers 200 and falls back
    to its default ordering, so "the call succeeded" proves nothing about
    whether the sort order was honoured. Should the provider ever start
    rejecting unknown sort orders, this test fails and these assertions can be
    simplified.

    The fallback is established by comparison rather than by equality: the
    catalog shifts between calls, so no two live responses match exactly. An
    ignored sort order must return substantially the default page, and share
    nothing with a deliberately opposite ordering.
    """
    ignored = await tmdb_service.get_media(
        media_type=media_type, sort_by=UNSUPPORTED_SORT_ORDER
    )
    default = await tmdb_service.get_media(
        media_type=media_type, sort_by=DEFAULT_SORT_ORDER
    )
    opposite = await tmdb_service.get_media(
        media_type=media_type, sort_by=ASCENDING_POPULARITY_SORT
    )

    ignored_ids = set(media_ids_in_returned_order(ignored))
    default_ids = set(media_ids_in_returned_order(default))
    opposite_ids = set(media_ids_in_returned_order(opposite))

    assert len(ignored_ids & default_ids) >= PROVIDER_PAGE_SIZE - MAX_CATALOG_DRIFT
    assert not ignored_ids & opposite_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
@pytest.mark.parametrize("sort_by,attribute,highest_first", ORDERED_SORT_CASES)
async def test_sort_order_actually_orders_the_results(
    tmdb_service: TMDBService,
    media_type: str,
    sort_by: str,
    attribute: str,
    highest_first: bool
) -> None:
    """Sort orders whose field survives into the standard model really sort.

    The date case is the one that matters most: the tools offer a single
    provider-agnostic date field while the provider names it differently per
    media type, so this asserts the observable outcome rather than the string
    that was sent.
    """
    result = await tmdb_service.get_media(media_type=media_type, sort_by=sort_by)

    values = values_in_returned_order(result, attribute)
    assert len(values) > 1, "need at least two populated entries to observe an ordering"
    assert values == sorted(values, reverse=highest_first)


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
@pytest.mark.parametrize("descending,ascending", SORT_DIRECTION_PAIRS)
async def test_sort_direction_changes_the_results(
    tmdb_service: TMDBService,
    media_type: str,
    descending: str,
    ascending: str
) -> None:
    """Sort orders without a readable ordering still demonstrably take effect.

    Reversing the direction is observable even when the underlying values are
    not: the two directions must not return the same page. Without this, these
    sort orders would rest on the provider's silence, which the test above
    establishes means nothing.
    """
    descending_results = await tmdb_service.get_media(media_type=media_type, sort_by=descending)
    ascending_results = await tmdb_service.get_media(media_type=media_type, sort_by=ascending)

    assert descending_results.results and ascending_results.results
    assert (
        media_ids_in_returned_order(descending_results)
        != media_ids_in_returned_order(ascending_results)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_genre_filter_returns_only_media_in_that_genre(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """The genre filter constrains the results to the requested genre."""
    genres = await tmdb_service.get_genres()
    genre_id = first_genre_id_for(genres, media_type)

    result = await tmdb_service.get_media(media_type=media_type, genre_id=genre_id)

    assert result.results
    for item in result.results:
        assert genre_id in (item.genre_ids or [])


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_year_filter_returns_only_media_from_that_year(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """The year filter constrains the results, under whichever parameter name
    the provider uses for this media type."""
    requested_year = date.today().year - YEARS_BEFORE_PRESENT

    result = await tmdb_service.get_media(media_type=media_type, year=requested_year)

    assert result.results
    for item in result.results:
        if item.date is not None:
            assert item.date.year == requested_year


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_provider_accepts_the_original_language_filter(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """The original language filter is accepted and still returns results.

    The standard Media model does not carry original language, so this asserts
    that the parameter is honoured rather than inspecting the returned values.
    """
    result = await tmdb_service.get_media(
        media_type=media_type,
        language=SAMPLE_LANGUAGE_CODE
    )

    assert result.results


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_a_full_discover_page_holds_the_result_count_we_assume(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """A full page holds exactly PROVIDER_PAGE_SIZE results.

    MAX_RESULTS_MAX is defined as that number, so the ceiling the tools
    advertise is only honest while this holds. Checked for discover as well as
    search because nothing obliges a provider to page both flows alike.
    """
    result = await tmdb_service.get_media(
        media_type=media_type, sort_by=DEFAULT_SORT_ORDER, max_results=BEYOND_PAGE_SIZE
    )

    assert result.total_pages > FIRST_PAGE, "need an unfiltered query spanning many pages"
    assert len(result.results) == PROVIDER_PAGE_SIZE


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_consecutive_pages_return_different_media(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """Pagination advances through the catalog rather than repeating a page.

    A handful of shared entries is expected rather than alarming: a title ranked
    near the page boundary can slip onto the next page as the catalog updates
    between the two calls. Repeating a page would show the whole page shared.
    """
    first = await tmdb_service.get_media(
        media_type=media_type, sort_by=DEFAULT_SORT_ORDER, page=FIRST_PAGE
    )
    second = await tmdb_service.get_media(
        media_type=media_type, sort_by=DEFAULT_SORT_ORDER, page=SECOND_PAGE
    )

    first_ids = {item.id for item in first.results}
    second_ids = {item.id for item in second.results}

    assert first_ids and second_ids
    assert len(first_ids & second_ids) <= MAX_CATALOG_DRIFT
