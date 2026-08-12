"""Tests on the API contract with TMDB for discovery concerns.

As of 2026, TMDB ignores unrecognized parameters (returns 200 code).
So asserting on a successful call does not test parameters well.
Instead, tests should inspect the returned payload.

Run with: uv run pytest -m external
"""

from datetime import date

import pytest

from greenroom.models.media import MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.params import DEFAULT_SORT_ORDER
from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.discovery.validation import VALID_SORT_OPTIONS

pytestmark = pytest.mark.external

#------------
# Fixtures
#------------

# TMDB uses different parameter names for films and TV, so every test runs both
MEDIA_TYPES = (MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION)

DESCENDING_DIRECTION = "desc"
ASCENDING_DIRECTION = "asc"

# How each sorting parameter (that is offered by MCP tools) is checked.
# None means the ordering cannot be read, so that sort is checked by comparing its two directions instead.
MEDIA_ATTRIBUTE_BY_SORT_ORDER: dict[str, str | None] = {
    "date.desc": "date",
    "date.asc": "date",

    # TMDB does not sort reliably on this metric as of 2026
    "vote_average.desc": None,
    "vote_average.asc": None,

    # Popularity is not carried on Media
    "popularity.desc": None,
    "popularity.asc": None,
}

#------------
# Helpers
#------------

def media_ids_in_returned_order(media_list: MediaList) -> list[str]:
    """Ids, in the order TMDB returned them."""
    return [item.id for item in media_list.results]

def media_attribute_for(sort_order: str) -> str | None:
    """Media attribute a sort order can be read from, or None if there is none.

    Raises KeyError for a sort order the tools offer that this file has no way
    to check, so a new option cannot be added without deciding how to cover it.
    """
    return MEDIA_ATTRIBUTE_BY_SORT_ORDER[sort_order]

VERIFIABLE_SORT_ORDERS = [
    sort_order for sort_order in VALID_SORT_OPTIONS
    if media_attribute_for(sort_order) is not None
]

def unverifiable_sort_pairs() -> list[tuple[str, str]]:
    """Sorts we cannot verify simply by observing properties of the result.

    Pairs each unverifiable sort field with its ascending/descending directions,
    so the two can be compared against each other instead.
    """
    pairs: list[tuple[str, str]] = []
    for sort_order in VALID_SORT_OPTIONS:
        if media_attribute_for(sort_order) is not None:
            continue

        field = sort_order.partition(".")[0]
        pair = (f"{field}.{DESCENDING_DIRECTION}", f"{field}.{ASCENDING_DIRECTION}")
        assert set(pair) <= set(VALID_SORT_OPTIONS), (
            f"{field} is offered in one direction only, so it cannot be checked this way"
        )

        if pair not in pairs:
            pairs.append(pair)

    return pairs

#------------
# Tests
#------------

@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
@pytest.mark.parametrize("sort_by", VERIFIABLE_SORT_ORDERS)
async def test_sort_order_actually_orders_the_results(
    tmdb_service: TMDBService,
    media_type: str,
    sort_by: str
) -> None:
    """TMDB really sorts by the field we asked for.

    The date cases matter most. The tools offer one "date" sort, while TMDB
    names that field differently for films and TV, so this checks the order of
    the results rather than the string we sent.
    """
    result = await tmdb_service.get_media(media_type=media_type, sort_by=sort_by)

    attribute = media_attribute_for(sort_by)
    # Skips entries where the attribute is missing. TMDB leaves dates and ratings
    # unset on some titles, and a gap says nothing about the order.
    all_values = [getattr(item, attribute) for item in result.results]
    values = [value for value in all_values if value is not None]

    assert len(values) > 1, "need at least two populated entries to observe an ordering"
    direction = sort_by.partition(".")[2]
    assert values == sorted(values, reverse=direction == DESCENDING_DIRECTION)


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
@pytest.mark.parametrize("descending,ascending", unverifiable_sort_pairs())
async def test_sort_direction_changes_the_results(
    tmdb_service: TMDBService,
    media_type: str,
    descending: str,
    ascending: str
) -> None:
    """Changing sort direction changes the order of results."""
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
    """Filtering by genre returns only media in that genre."""
    # Read the genre from TMDB rather than hardcoded, so the test does not embed
    # genre data that can change. The lowest id keeps every run on the same genre.
    endpoint = f"/genre/{tmdb_service.config_map[media_type].endpoint}/list"
    payload = await tmdb_service.client.get(endpoint, {})
    genre_ids = [entry["id"] for entry in payload["genres"]]
    assert genre_ids, f"TMDB published no genres for {media_type}"
    genre_id = min(genre_ids)

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
    """Filtering by year returns only media from that year."""
    requested_year = date.today().year - 2 # two years ago
    result = await tmdb_service.get_media(media_type=media_type, year=requested_year)

    assert result.results
    for item in result.results:
        if item.date is not None:
            assert item.date.year == requested_year


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_original_language_filter_changes_which_media_are_returned(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """Filtering by original language changes which media come back."""
    sample = await tmdb_service.get_media(
        media_type=media_type,
        language="en"
    )
    alternate = await tmdb_service.get_media(
        media_type=media_type,
        language="fr"
    )

    sample_ids = set(media_ids_in_returned_order(sample))
    alternate_ids = set(media_ids_in_returned_order(alternate))

    assert sample_ids and alternate_ids
    assert not sample_ids & alternate_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", MEDIA_TYPES)
async def test_a_full_discover_page_holds_the_result_count_we_assume(
    tmdb_service: TMDBService,
    media_type: str
) -> None:
    """A full page holds exactly PROVIDER_PAGE_SIZE results.
    This value is relevant upstream for bounding parameters like max_results.
    """
    endpoint = f"/discover/{tmdb_service.config_map[media_type].endpoint}"
    payload = await tmdb_service.client.get(endpoint, {"sort_by": DEFAULT_SORT_ORDER})

    assert payload["total_pages"] > 1, "need an unfiltered query spanning many pages"
    assert len(payload["results"]) == PROVIDER_PAGE_SIZE
