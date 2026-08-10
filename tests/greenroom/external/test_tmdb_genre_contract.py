"""Contract tests for the genre catalog the tools read from TMDB.

The mood map hardcodes genre names, and the service merges two provider
catalogs by name. Both rest on assumptions about data owned by the provider,
which only the provider can confirm.

Run with: uv run pytest -m external
"""

import pytest

from greenroom.config import GENRE_MOOD_MAP
from greenroom.models.genre import GenreList
from greenroom.services.tmdb.service import TMDBService

pytestmark = pytest.mark.external

# TMDB publishes a separate genre catalog per media type
FILM_GENRE_ENDPOINT = "/genre/movie/list"
TELEVISION_GENRE_ENDPOINT = "/genre/tv/list"
GENRE_ENDPOINTS = (FILM_GENRE_ENDPOINT, TELEVISION_GENRE_ENDPOINT)


def names_in(genres: GenreList) -> set[str]:
    """Genre names in the merged catalog the tools expose."""
    return {genre.name for genre in genres.genres}


async def genre_ids_by_name(service: TMDBService, endpoint: str) -> dict[str, int]:
    """Name to id, straight from one of the provider's genre endpoints.

    Read unmerged so that tests can assert on what the provider actually
    publishes per media type, rather than on the combined view.
    """
    payload = await service.client.get(endpoint, {})

    return {entry["name"]: entry["id"] for entry in payload["genres"]}


@pytest.mark.asyncio
async def test_every_mood_mapped_genre_exists_in_the_live_catalog(
    tmdb_service: TMDBService
) -> None:
    """Every genre the mood map hardcodes is still published by the provider.

    categorize_genres keys its hardcoded mappings by genre name. A genre the
    provider renames or retires does not raise anything: the mapping quietly
    stops matching and that genre falls through to the LLM fallback, so the
    tool keeps answering while steadily losing its curated categorisation.

    Only this direction is asserted. Catalog genres absent from the map are
    expected, and handling them is exactly what the fallback exists for.
    """
    genres = await tmdb_service.get_genres()

    unmatched = set(GENRE_MOOD_MAP) - names_in(genres)

    assert not unmatched, (
        f"mood map references genres the provider no longer publishes: {sorted(unmatched)}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", GENRE_ENDPOINTS)
async def test_provider_publishes_a_populated_genre_catalog(
    tmdb_service: TMDBService,
    endpoint: str
) -> None:
    """Each genre endpoint returns usable entries.

    The service drops genre entries that fail schema validation without
    raising, so a payload change at the provider would show up as a quietly
    shrinking catalog rather than as an error.
    """
    ids_by_name = await genre_ids_by_name(tmdb_service, endpoint)

    assert ids_by_name, f"provider published no genres at {endpoint}"
    assert all(name.strip() for name in ids_by_name)
    assert all(isinstance(genre_id, int) for genre_id in ids_by_name.values())


@pytest.mark.asyncio
async def test_genre_names_shared_by_both_media_types_carry_one_id(
    tmdb_service: TMDBService
) -> None:
    """A genre name published for both media types means the same id in both.

    The service merges the two catalogs by name and keeps a single id per
    name, so a name that meant different ids per media type would be reported
    with the wrong one for whichever media type lost the merge.
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


@pytest.mark.asyncio
async def test_merged_catalog_reports_availability_matching_the_provider(
    tmdb_service: TMDBService
) -> None:
    """Availability flags agree with which catalogs the provider listed the genre in.

    These flags are how callers decide whether a genre id is usable for a
    discover request, so a merge that mislabels them sends callers to filters
    that return nothing.
    """
    film_ids = await genre_ids_by_name(tmdb_service, FILM_GENRE_ENDPOINT)
    television_ids = await genre_ids_by_name(tmdb_service, TELEVISION_GENRE_ENDPOINT)

    merged = await tmdb_service.get_genres()

    assert merged.genres
    for genre in merged.genres:
        assert genre.has_films == (genre.name in film_ids), genre.name
        assert genre.has_tv_shows == (genre.name in television_ids), genre.name
