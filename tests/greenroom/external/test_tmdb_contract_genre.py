"""Tests on the API contract with TMDB for genre concerns.

Run with: uv run pytest -m external
"""

from typing import Any

import pytest
from pydantic import ValidationError

from greenroom.services.tmdb.models import TMDBGenre
from greenroom.services.tmdb.service import TMDBService

pytestmark = pytest.mark.external

FILM_GENRE_ENDPOINT = "/genre/movie/list"
TELEVISION_GENRE_ENDPOINT = "/genre/tv/list"
GENRE_ENDPOINTS = (FILM_GENRE_ENDPOINT, TELEVISION_GENRE_ENDPOINT)

#------------
# Helpers
#------------

async def genre_entries(service: TMDBService, endpoint: str) -> list[dict[str, Any]]:
    """Raw genre entries from one of TMDB's genre endpoints."""
    payload = await service.client.get(endpoint, {})

    return payload["genres"]


async def genre_ids_by_name(service: TMDBService, endpoint: str) -> dict[str, int]:
    """Name to id, read straight from one of TMDB's genre endpoints.

    Read before merging, so tests can check what TMDB publishes for a single
    media type instead of the combined list.
    """
    entries = await genre_entries(service, endpoint)

    return {entry["name"]: entry["id"] for entry in entries}

#------------
# Tests
#------------

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", GENRE_ENDPOINTS)
async def test_every_published_genre_still_passes_the_services_validation(
    tmdb_service: TMDBService,
    endpoint: str
) -> None:
    """Every genre TMDB publishes survives the model validation (structure is as-expected)."""
    entries = await genre_entries(tmdb_service, endpoint)
    assert entries, f"TMDB published no genres at {endpoint}"

    for entry in entries:
        try:
            TMDBGenre(**entry)
        except ValidationError as error:
            pytest.fail(f"TMDB genre entry no longer parses: {entry} ({error})")


@pytest.mark.asyncio
async def test_genre_names_shared_by_both_media_types_carry_one_id(
    tmdb_service: TMDBService
) -> None:
    """A genre published for both media types has the same id in both.

    The TMDB service merges the two lists by name and keeps one id per name
    so we want to know if the TMDB ids begin to diverge unexpectedly.
    """
    film_ids = await genre_ids_by_name(tmdb_service, FILM_GENRE_ENDPOINT)
    television_ids = await genre_ids_by_name(tmdb_service, TELEVISION_GENRE_ENDPOINT)

    shared_names = set(film_ids) & set(television_ids)
    assert shared_names, "expected at least one genre published for both media types"

    conflicting = {
        name: (film_ids[name], television_ids[name])
        for name in shared_names
        if film_ids[name] != television_ids[name]
    }

    assert not conflicting, f"genre names carrying different ids per media type: {conflicting}"
