"""Tests that the media and genre tools compose into the journeys an agent actually runs.

A common scenario is a user naming a title they liked and asking for similar recommendations.
An agent serves that by calling a search tool, resolving the result's genres through the genre tools,
and then calling a discover tool.

This test file covers the seam between those tools, which are otherwise extensively covered by unit tests.
"""

from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from greenroom.config import GENRE_MOOD_MAP, Mood
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import (
    DISCOVER_MAX_RESULTS,
    PROVIDER_PAGE_SIZE,
    SEARCH_MAX_RESULTS,
)

from .conftest import (
    EMPTY_MEDIA_RESPONSE,
    FILM_DISCOVER_PATH,
    FILM_DISCOVER_URL,
    FILM_GENRE_LIST_URL,
    FILM_ONLY_GENRE_ID,
    FILM_RESPONSE_FIELDS,
    FILM_SEARCH_URL,
    PROVIDER_NAME,
    SHARED_GENRE_ID,
    TELEVISION_DISCOVER_PATH,
    TELEVISION_DISCOVER_URL,
    TELEVISION_GENRE_LIST_URL,
    TELEVISION_ONLY_GENRE_ID,
    TELEVISION_RESPONSE_FIELDS,
    TELEVISION_SEARCH_URL,
    SamplingRecorder,
    build_genre_response,
    build_media_response,
    requests_to,
)


SEED_QUERY = "sample-seed-title"
NO_MATCH_QUERY = "no-match-query-000"

# Enough results that "every result carries the genre" is a real claim
SIMILAR_RESULT_COUNT = 3

PROVIDER_ERROR_STATUS = 500


# =============================================================================
# Search hands a genre to discover
# =============================================================================


@pytest.mark.asyncio
async def test_film_genre_from_search_drives_discover(complete_server, httpx_mock):
    """A genre id read off a search_films result is accepted by discover_films."""
    httpx_mock.add_response(
        url=FILM_SEARCH_URL,
        json=build_media_response(
            *FILM_RESPONSE_FIELDS, genre_ids=[FILM_ONLY_GENRE_ID, SHARED_GENRE_ID]
        )
    )
    httpx_mock.add_response(
        url=FILM_DISCOVER_URL,
        json=build_media_response(
            *FILM_RESPONSE_FIELDS, genre_ids=[FILM_ONLY_GENRE_ID], count=SIMILAR_RESULT_COUNT
        )
    )

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": SEED_QUERY})
        seed_genre_id = found.structured_content["results"][0]["genre_ids"][0]

        similar = await client.call_tool("discover_films", {"genre_id": seed_genre_id})

    # The id the agent read off the search payload is the one that reached the provider
    discover_request = requests_to(httpx_mock, FILM_DISCOVER_PATH)[0]
    assert discover_request.url.params["with_genres"] == str(seed_genre_id)

    results = similar.structured_content["results"]
    assert len(results) == SIMILAR_RESULT_COUNT
    assert all(seed_genre_id in result["genre_ids"] for result in results)
    assert all(result["media_type"] == MEDIA_TYPE_FILM for result in results)


@pytest.mark.asyncio
async def test_television_genre_from_search_drives_discover(complete_server, httpx_mock):
    """A genre id read off a search_television result is accepted by discover_television."""
    httpx_mock.add_response(
        url=TELEVISION_SEARCH_URL,
        json=build_media_response(
            *TELEVISION_RESPONSE_FIELDS, genre_ids=[TELEVISION_ONLY_GENRE_ID, SHARED_GENRE_ID]
        )
    )
    httpx_mock.add_response(
        url=TELEVISION_DISCOVER_URL,
        json=build_media_response(
            *TELEVISION_RESPONSE_FIELDS,
            genre_ids=[TELEVISION_ONLY_GENRE_ID],
            count=SIMILAR_RESULT_COUNT
        )
    )

    async with Client(complete_server) as client:
        found = await client.call_tool("search_television", {"query": SEED_QUERY})
        seed_genre_id = found.structured_content["results"][0]["genre_ids"][0]

        similar = await client.call_tool("discover_television", {"genre_id": seed_genre_id})

    discover_request = requests_to(httpx_mock, TELEVISION_DISCOVER_PATH)[0]
    assert discover_request.url.params["with_genres"] == str(seed_genre_id)

    results = similar.structured_content["results"]
    assert len(results) == SIMILAR_RESULT_COUNT
    assert all(seed_genre_id in result["genre_ids"] for result in results)
    assert all(result["media_type"] == MEDIA_TYPE_TELEVISION for result in results)


# =============================================================================
# Search and the genre catalog share a vocabulary
# =============================================================================

SEARCH_CASES = [
    ("search_films", FILM_SEARCH_URL, FILM_RESPONSE_FIELDS, [FILM_ONLY_GENRE_ID, SHARED_GENRE_ID]),
    (
        "search_television",
        TELEVISION_SEARCH_URL,
        TELEVISION_RESPONSE_FIELDS,
        [SHARED_GENRE_ID, TELEVISION_ONLY_GENRE_ID]
    ),
]

SEARCH_CASE_IDS = [tool_name for tool_name, *_ in SEARCH_CASES]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,search_url,response_fields,genre_ids", SEARCH_CASES, ids=SEARCH_CASE_IDS)
async def test_genre_ids_from_search_exist_in_genre_catalog(
    complete_server,
    httpx_mock,
    genre_endpoints,
    tool_name: str,
    search_url: Any,
    response_fields: tuple[str, str],
    genre_ids: list[int]
):
    """Every genre id a search result carries can be named through list_genres."""
    httpx_mock.add_response(
        url=search_url,
        json=build_media_response(*response_fields, genre_ids=genre_ids)
    )

    async with Client(complete_server) as client:
        found = await client.call_tool(tool_name, {"query": SEED_QUERY})
        catalog = (await client.call_tool("list_genres", {})).structured_content

    published_ids = {properties["id"] for properties in catalog.values()}
    returned_ids = {
        genre_id
        for result in found.structured_content["results"]
        for genre_id in result["genre_ids"]
    }

    assert returned_ids
    assert returned_ids <= published_ids


@pytest.mark.asyncio
async def test_cross_media_handoff_resolves_through_genre_name(
    complete_server, httpx_mock, genre_endpoints
):
    """The catalog carries the flag an agent needs to take a film genre over to television.

    Films and television carry separate genre vocabularies at the provider, so an agent that forwarded
    a film-only id to discover_television would filter on a genre television does not have.
    """
    httpx_mock.add_response(
        url=FILM_SEARCH_URL,
        json=build_media_response(
            *FILM_RESPONSE_FIELDS, genre_ids=[FILM_ONLY_GENRE_ID, SHARED_GENRE_ID]
        )
    )
    httpx_mock.add_response(
        url=TELEVISION_DISCOVER_URL,
        json=build_media_response(
            *TELEVISION_RESPONSE_FIELDS, genre_ids=[SHARED_GENRE_ID], count=SIMILAR_RESULT_COUNT
        )
    )

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": SEED_QUERY})
        catalog = (await client.call_tool("list_genres", {})).structured_content

        film_genre_ids = found.structured_content["results"][0]["genre_ids"]
        television_ready_ids = [
            properties["id"]
            for properties in catalog.values()
            if properties["has_tv_shows"] and properties["id"] in film_genre_ids
        ]

        # The film-only genre is filtered out before television is ever asked about it
        assert television_ready_ids == [SHARED_GENRE_ID]

        similar = await client.call_tool(
            "discover_television", {"genre_id": television_ready_ids[0]}
        )

    discover_request = requests_to(httpx_mock, TELEVISION_DISCOVER_PATH)[0]
    assert discover_request.url.params["with_genres"] == str(SHARED_GENRE_ID)

    results = similar.structured_content["results"]
    assert len(results) == SIMILAR_RESULT_COUNT
    assert all(result["media_type"] == MEDIA_TYPE_TELEVISION for result in results)


# =============================================================================
# Mood buckets lead back to discoverable genres
# =============================================================================

# Drawn from the production mood map so that the bucketing under test is driven by
# real configuration rather than by a genre name invented here
FUN_GENRE_NAME = next(name for name, mood in GENRE_MOOD_MAP.items() if mood is Mood.FUN)
SERIOUS_GENRE_NAME = next(name for name, mood in GENRE_MOOD_MAP.items() if mood is Mood.SERIOUS)

# Ids distinct from the shared catalog's, so a mix-up between the two catalogs shows up
FUN_GENRE_ID = 811
SERIOUS_GENRE_ID = 812

MOOD_MAPPED_CATALOG = {FUN_GENRE_NAME: FUN_GENRE_ID, SERIOUS_GENRE_NAME: SERIOUS_GENRE_ID}


@pytest.mark.asyncio
async def test_mood_bucket_names_resolve_to_discoverable_genres(complete_server, httpx_mock):
    """A name that categorize_genres puts in a mood bucket resolves to an id discover_films accepts.

    categorize_genres answers in names while discover_films takes an id, so the two
    compose only if the mood map in config.py speaks the same vocabulary as the provider catalog.
    """
    catalog_response = build_genre_response(MOOD_MAPPED_CATALOG)
    httpx_mock.add_response(url=FILM_GENRE_LIST_URL, json=catalog_response, is_reusable=True)
    httpx_mock.add_response(url=TELEVISION_GENRE_LIST_URL, json=catalog_response, is_reusable=True)
    httpx_mock.add_response(
        url=FILM_DISCOVER_URL,
        json=build_media_response(
            *FILM_RESPONSE_FIELDS, genre_ids=[FUN_GENRE_ID], count=SIMILAR_RESULT_COUNT
        )
    )

    recorder = SamplingRecorder(reply=Mood.OTHER.value)

    async with Client(complete_server, sampling_handler=recorder) as client:
        buckets = (await client.call_tool("categorize_genres", {})).structured_content
        catalog = (await client.call_tool("list_genres", {})).structured_content

        assert buckets[Mood.FUN.value] == [FUN_GENRE_NAME]

        similar = await client.call_tool(
            "discover_films", {"genre_id": catalog[FUN_GENRE_NAME]["id"]}
        )

    # No bucketed name is a dead end, since the catalog can turn each one back into an id
    bucketed_names = {name for names in buckets.values() for name in names}
    assert bucketed_names == set(MOOD_MAPPED_CATALOG)
    assert bucketed_names <= set(catalog)

    # Names the mood map already knows cost no sampling round trip
    assert recorder.requests == []

    discover_request = requests_to(httpx_mock, FILM_DISCOVER_PATH)[0]
    assert discover_request.url.params["with_genres"] == str(FUN_GENRE_ID)
    assert len(similar.structured_content["results"]) == SIMILAR_RESULT_COUNT


# =============================================================================
# Journeys that cannot continue
# =============================================================================


@pytest.mark.asyncio
async def test_empty_search_result_ends_journey_without_error(complete_server, httpx_mock):
    """A search that matches nothing returns an empty page rather than failing the journey."""
    httpx_mock.add_response(url=FILM_SEARCH_URL, json=EMPTY_MEDIA_RESPONSE)

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": NO_MATCH_QUERY})

    payload = found.structured_content
    assert payload["results"] == []
    assert payload["total_results"] == 0
    assert payload["provider"] == PROVIDER_NAME


@pytest.mark.asyncio
async def test_search_result_without_genres_still_permits_discovery(complete_server, httpx_mock):
    """A title carrying no genres leaves nothing to hand off, and unfiltered discovery still works.

    Dropping the genre filter is the caller's decision rather than something the server does.
    What is asserted here is that discover_films sends no genre filter when it is given no
    genre_id. So a journey that loses its seed genre still comes back with recommendations.
    """
    httpx_mock.add_response(
        url=FILM_SEARCH_URL,
        json=build_media_response(*FILM_RESPONSE_FIELDS, genre_ids=[])
    )
    httpx_mock.add_response(
        url=FILM_DISCOVER_URL,
        json=build_media_response(
            *FILM_RESPONSE_FIELDS, genre_ids=[SHARED_GENRE_ID], count=SIMILAR_RESULT_COUNT
        )
    )

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": SEED_QUERY})

        assert found.structured_content["results"][0]["genre_ids"] == []

        similar = await client.call_tool("discover_films", {})

    # With no genre supplied, the request goes out unfiltered instead of carrying a guessed one
    discover_request = requests_to(httpx_mock, FILM_DISCOVER_PATH)[0]
    assert "with_genres" not in discover_request.url.params

    assert len(similar.structured_content["results"]) == SIMILAR_RESULT_COUNT


@pytest.mark.asyncio
async def test_provider_failure_on_second_leg_surfaces_as_tool_error(complete_server, httpx_mock):
    """A provider failure during discovery reaches the agent as a tool error.

    The search/lookup leg has already responded by this point in the flow
    so the failure should arrive as an error rather than as a empty recommendation (silent failure).
    """
    httpx_mock.add_response(
        url=FILM_SEARCH_URL,
        json=build_media_response(*FILM_RESPONSE_FIELDS, genre_ids=[SHARED_GENRE_ID])
    )
    httpx_mock.add_response(url=FILM_DISCOVER_URL, status_code=PROVIDER_ERROR_STATUS)

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": SEED_QUERY})

        with pytest.raises(ToolError, match=f"{PROVIDER_NAME} API error: {PROVIDER_ERROR_STATUS}"):
            await client.call_tool("discover_films", {"genre_id": SHARED_GENRE_ID})

    assert found.structured_content["results"][0]["genre_ids"] == [SHARED_GENRE_ID]


# =============================================================================
# The two flows keep their own limits
# =============================================================================


@pytest.mark.asyncio
async def test_each_tool_honors_its_own_result_limit_in_one_session(complete_server, httpx_mock):
    """Search and discover keep their own default result counts even though they share formatting.

    Both flows pass through format_media_list, and a search asking for a specific
    title wants a short list while browsing wants a full page. Serving both from one
    provider page is what would expose a limit leaking from one flow into the other.
    """
    full_page = build_media_response(
        *FILM_RESPONSE_FIELDS, genre_ids=[SHARED_GENRE_ID], count=PROVIDER_PAGE_SIZE
    )
    httpx_mock.add_response(url=FILM_SEARCH_URL, json=full_page)
    httpx_mock.add_response(url=FILM_DISCOVER_URL, json=full_page)

    async with Client(complete_server) as client:
        found = await client.call_tool("search_films", {"query": SEED_QUERY})
        similar = await client.call_tool("discover_films", {"genre_id": SHARED_GENRE_ID})

    assert len(found.structured_content["results"]) == SEARCH_MAX_RESULTS
    assert len(similar.structured_content["results"]) == DISCOVER_MAX_RESULTS
