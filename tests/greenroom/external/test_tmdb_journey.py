"""Smoke Test: Journey from a title a user named to titles like it including a real network call to provider.


The offline (non-external) counterpart to this test suite resides in tools/test_tool_integrations.py.
The non-external tests assert on the plumbing against mocked payloads (no network calls).

This test runs the same journey against the real provider, which is the only way to catch drift
between the genre ids a search result returns and the ids the genre catalog publishes.
The seed title is read from the provider (not hardcoded) and the assertions run through
the orchestration methods so that the mapping layer production uses is the one under test.
"""

import pytest

from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.genre_tools import fetch_genres
from greenroom.tools.media.discover_tools import browse_films
from greenroom.tools.media.search_tools import lookup_films

pytestmark = pytest.mark.external

POPULARITY_SORT = "popularity.desc"


@pytest.mark.asyncio
async def test_film_journey_from_title_to_similar_films(tmdb_service: TMDBService) -> None:
    """A genre carried by a real film leads to more films that share it.

    This is the recommendation scenario end to end: look up a title the user named,
    read a genre off it, name that genre from the catalog, then browse for more.
    """
    popular = await browse_films(
        tmdb_service, sort_by=POPULARITY_SORT, max_results=PROVIDER_PAGE_SIZE
    )
    seed_title = popular["results"][0]["title"]

    found = await lookup_films(tmdb_service, seed_title, max_results=PROVIDER_PAGE_SIZE)
    seeded = next((result for result in found["results"] if result["genre_ids"]), None)
    assert seeded is not None, f"no match for {seed_title!r} carried a genre"

    # Every genre the film reports is one the catalog can name,
    # so an agent can both explain the recommendation and reuse the id.
    catalog = await fetch_genres(tmdb_service)
    published_ids = {properties["id"] for properties in catalog.values()}
    assert set(seeded["genre_ids"]) <= published_ids

    seed_genre_id = seeded["genre_ids"][0]
    similar = await browse_films(
        tmdb_service, genre_id=seed_genre_id, max_results=PROVIDER_PAGE_SIZE
    )

    assert similar["results"]
    assert all(seed_genre_id in result["genre_ids"] for result in similar["results"])
