"""Tests for TMDBService.get_media()."""

import httpx
import pytest
from datetime import date
from urllib.parse import quote, urlencode
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.services.media_limits import DISCOVER_MAX_RESULTS, PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION

from .conftest import (
    TMDB_BASE_URL,
    TEST_API_KEY,
    TRUNCATED_MAX_RESULTS,
    SampleMedia,
    build_oversized_page,
)

# Response body for tests that assert on the outgoing request rather than the results
EMPTY_DISCOVER_RESPONSE = {
    "page": 1,
    "total_results": 0,
    "total_pages": 0,
    "results": []
}

# A page other than the default, for checking the page argument reaches TMDB
REQUESTED_PAGE = 2

# Entries on the sample result pages. Each holds only what the mapper copies
# verbatim, so the mocked payload and the expected Media can share it.
FILM_ONE = SampleMedia(
    title="Test Film One",
    description="Sample description for the first sample film.",
    rating=7.5,
    genre_ids=[18, 53],
)
FILM_TWO = SampleMedia(
    title="Test Film Two",
    description="Sample description for the second sample film.",
    rating=8.0,
    genre_ids=[80, 18],
)
TELEVISION_ONE = SampleMedia(
    title="Test Show One",
    description="Sample description for the first sample television show.",
    rating=7.8,
    genre_ids=[10765, 18, 10759],
)
TELEVISION_TWO = SampleMedia(
    title="Test Show Two",
    description="Sample description for the second sample television show.",
    rating=8.2,
    genre_ids=[18, 80],
)


def build_discover_url(endpoint: str, **extra_params: object) -> str:
    """Build the TMDB discover URL that the service is expected to request.

    Args:
        endpoint: TMDB endpoint segment ("movie" or "tv")
        extra_params: Additional expected params, and overrides for the defaults

    Returns:
        Fully encoded TMDB discover URL
    """
    params: dict[str, object] = {
        "api_key": TEST_API_KEY,
        "sort_by": "popularity.desc",
        "page": 1,
        "include_adult": "false",
        "include_video": "false",
    }
    params.update(extra_params)
    return f"{TMDB_BASE_URL}/discover/{endpoint}?{urlencode(params, quote_via=quote)}"


@pytest.mark.asyncio
async def test_get_media_returns_media_list_for_films(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media returns properly formatted MediaList for films."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {
                "id": 1,
                "title": FILM_ONE.title,
                "release_date": "2024-01-01",
                "vote_average": FILM_ONE.rating,
                "overview": FILM_ONE.description,
                "genre_ids": FILM_ONE.genre_ids,
                "poster_path": "/path.jpg"
            },
            {
                "id": 2,
                "title": FILM_TWO.title,
                "release_date": "2024-02-02",
                "vote_average": FILM_TWO.rating,
                "overview": FILM_TWO.description,
                "genre_ids": FILM_TWO.genre_ids,
                "popularity": 50.0
            }
        ]
    }

    httpx_mock.add_response(
        url=build_discover_url("movie", with_genres=18, primary_release_year=2024),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_FILM, genre_id=18, year=2024, page=1)

    # Compared whole, so a field this test forgot to name cannot drift unnoticed.
    # This also pins down that provider-only fields (poster_path, popularity)
    # are dropped rather than carried onto Media.
    assert result == MediaList(
        page=1,
        total_results=100,
        total_pages=5,
        results=[
            Media(
                id="1",
                media_type=MEDIA_TYPE_FILM,
                title=FILM_ONE.title,
                date=date(2024, 1, 1),
                rating=FILM_ONE.rating,
                description=FILM_ONE.description,
                genre_ids=FILM_ONE.genre_ids,
            ),
            Media(
                id="2",
                media_type=MEDIA_TYPE_FILM,
                title=FILM_TWO.title,
                date=date(2024, 2, 2),
                rating=FILM_TWO.rating,
                description=FILM_TWO.description,
                genre_ids=FILM_TWO.genre_ids,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_media_returns_media_list_for_television(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media returns properly formatted MediaList for television shows."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 50,
        "total_pages": 3,
        "results": [
            {
                "id": 3,
                "name": TELEVISION_ONE.title,
                "first_air_date": "2024-03-03",
                "vote_average": TELEVISION_ONE.rating,
                "overview": TELEVISION_ONE.description,
                "genre_ids": TELEVISION_ONE.genre_ids,
            },
            {
                "id": 4,
                "name": TELEVISION_TWO.title,
                "first_air_date": "2024-04-04",
                "vote_average": TELEVISION_TWO.rating,
                "overview": TELEVISION_TWO.description,
                "genre_ids": TELEVISION_TWO.genre_ids,
            }
        ]
    }

    httpx_mock.add_response(
        url=build_discover_url("tv", with_genres=18, first_air_date_year=2024),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_TELEVISION, genre_id=18, year=2024, page=1)

    # Compared whole, so a field this test forgot to name cannot drift unnoticed.
    # TMDB names the television title and date fields differently from films
    # (name/first_air_date), so this pins down that mapping too.
    assert result == MediaList(
        page=1,
        total_results=50,
        total_pages=3,
        results=[
            Media(
                id="3",
                media_type=MEDIA_TYPE_TELEVISION,
                title=TELEVISION_ONE.title,
                date=date(2024, 3, 3),
                rating=TELEVISION_ONE.rating,
                description=TELEVISION_ONE.description,
                genre_ids=TELEVISION_ONE.genre_ids,
            ),
            Media(
                id="4",
                media_type=MEDIA_TYPE_TELEVISION,
                title=TELEVISION_TWO.title,
                date=date(2024, 4, 4),
                rating=TELEVISION_TWO.rating,
                description=TELEVISION_TWO.description,
                genre_ids=TELEVISION_TWO.genre_ids,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_media_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that media with missing optional fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 5,
        "total_pages": 1,
        "results": [
            {"id": 1, "title": "Complete Film", "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Full details", "genre_ids": [28]},
            {"id": 2, "title": "Missing Date"},  # No release_date
            {"id": 3, "vote_average": 6.0},  # No title
            {"id": 4},  # Only ID
            {"id": 5, "title": "Invalid Date Film", "release_date": "not-a-date"},  # Invalid date format
            {"title": "No ID"},  # Missing ID - should be filtered out
        ]
    }

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=mock_response
    )

    service = TMDBService()

    # IMPORTANT: max_results must be passed explicitly in this test to ensure
    # that the default value for that field is not the source of truncation/filtering.
    # If we don't override max_results here and the default value (e.g., DISCOVER_MAX_RESULTS)
    # happens to be smaller than the set of mocked results, then this test
    # would pass whether or not a malformed entry was actually filtered out.
    result = await service.get_media(
        media_type=MEDIA_TYPE_FILM, max_results=PROVIDER_PAGE_SIZE
    )

    # Keyed by id rather than position, so reordering the mock above does not
    # disturb the expectations below. This test is about how each malformed
    # entry is mapped, not about the order the provider returned them in.
    by_id = {media.id: media for media in result.results}

    # The entry with no id is dropped rather than failing the whole page
    assert set(by_id) == {"1", "2", "3", "4", "5"}

    # Compared whole, so a field this test forgot to name cannot drift unnoticed
    assert by_id["1"] == Media(
        id="1",
        media_type=MEDIA_TYPE_FILM,
        title="Complete Film",
        date=date(2024, 1, 1),
        rating=7.5,
        description="Full details",
        genre_ids=[28],
    )

    # Absent fields fall back instead of raising: title to "", the rest to
    # None, and genre_ids to an empty list
    assert by_id["2"] == Media(
        id="2", media_type=MEDIA_TYPE_FILM, title="Missing Date", genre_ids=[]
    )
    assert by_id["3"] == Media(
        id="3", media_type=MEDIA_TYPE_FILM, title="", rating=6.0, genre_ids=[]
    )
    assert by_id["4"] == Media(
        id="4", media_type=MEDIA_TYPE_FILM, title="", genre_ids=[]
    )

    # An unparseable date is treated as absent rather than propagated
    assert by_id["5"] == Media(
        id="5", media_type=MEDIA_TYPE_FILM, title="Invalid Date Film", genre_ids=[]
    )


@pytest.mark.asyncio
async def test_get_media_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media handles empty results gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_FILM)

    assert result.results == []
    assert result.total_results == 0
    assert result.page == 1
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_get_media_uses_default_parameters(monkeypatch, httpx_mock: HTTPXMock):
    """Test that get_media applies correct default parameters."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=mock_response
    )

    service = TMDBService()
    await service.get_media(media_type=MEDIA_TYPE_FILM)

    # Verify the mock was called with correct default URL
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert "sort_by=popularity.desc" in str(request.url)
    assert "page=1" in str(request.url)
    assert "include_adult=false" in str(request.url)


@pytest.mark.asyncio
async def test_get_media_limits_results_to_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media truncates the result list to max_results."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    returned_count = DISCOVER_MAX_RESULTS + 5
    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=build_oversized_page(returned_count)
    )

    service = TMDBService()
    result = await service.get_media(
        media_type=MEDIA_TYPE_FILM, max_results=TRUNCATED_MAX_RESULTS
    )

    assert len(result.results) == TRUNCATED_MAX_RESULTS
    # total_results still reflects what TMDB reported, not the truncated count
    assert result.total_results == returned_count


@pytest.mark.asyncio
async def test_get_media_applies_discover_max_results_by_default(monkeypatch, httpx_mock: HTTPXMock):
    """Test that omitting max_results truncates to the discover default.

    The default is what an agent gets when it does not ask for a count, so a
    signature that drifted from media_limits would quietly change every
    unqualified call.
    """
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=build_oversized_page(DISCOVER_MAX_RESULTS + 5)
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_FILM)

    assert len(result.results) == DISCOVER_MAX_RESULTS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media_type,endpoint",
    [
        (MEDIA_TYPE_FILM, "movie"),
        (MEDIA_TYPE_TELEVISION, "tv"),
    ]
)
async def test_get_media_requests_the_page_it_was_given(
    monkeypatch,
    httpx_mock: HTTPXMock,
    media_type,
    endpoint
):
    """Test that a page other than the default is sent to TMDB.

    Every other test here requests page 1, which a dropped page argument would
    still satisfy.
    """
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=build_discover_url(endpoint, page=REQUESTED_PAGE),
        json=EMPTY_DISCOVER_RESPONSE
    )

    service = TMDBService()
    await service.get_media(media_type=media_type, page=REQUESTED_PAGE)

    request = httpx_mock.get_requests()[0]
    assert f"page={REQUESTED_PAGE}" in str(request.url)


@pytest.mark.asyncio
async def test_get_media_filters_by_original_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test original_language parameter filters media correctly."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {"id": 123, "title": "Spanish Film", "original_language": "es"}
        ]
    }

    httpx_mock.add_response(
        url=build_discover_url("movie", with_original_language="es"),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_FILM, original_language="es")

    assert len(result.results) == 1
    assert result.results[0].title == "Spanish Film"

    # Verify the URL included the original language parameter
    request = httpx_mock.get_requests()[0]
    assert "with_original_language=es" in str(request.url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media_type,requested_sort,expected_sort",
    [
        (MEDIA_TYPE_FILM, "date.desc", "release_date.desc"),
        (MEDIA_TYPE_FILM, "date.asc", "release_date.asc"),
        (MEDIA_TYPE_TELEVISION, "date.desc", "first_air_date.desc"),
        (MEDIA_TYPE_TELEVISION, "date.asc", "first_air_date.asc"),
    ]
)
async def test_get_media_translates_date_sort_to_provider_field(
    monkeypatch,
    httpx_mock: HTTPXMock,
    media_type: str,
    requested_sort: str,
    expected_sort: str
) -> None:
    """Test that the generic date sort order becomes TMDB's per-media-type date field.

    The tools expose a provider-agnostic "date" sort order, but TMDB names its
    date field differently for films and television and rejects "date" itself.
    """
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(json=EMPTY_DISCOVER_RESPONSE)

    service = TMDBService()
    await service.get_media(media_type=media_type, sort_by=requested_sort)

    request = httpx_mock.get_requests()[0]
    assert f"sort_by={expected_sort}" in str(request.url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media_type,requested_sort",
    [
        (MEDIA_TYPE_FILM, "popularity.asc"),
        (MEDIA_TYPE_FILM, "vote_average.desc"),
        (MEDIA_TYPE_TELEVISION, "popularity.desc"),
        (MEDIA_TYPE_TELEVISION, "vote_average.asc"),
    ]
)
async def test_get_media_forwards_provider_native_sort_unchanged(
    monkeypatch,
    httpx_mock: HTTPXMock,
    media_type: str,
    requested_sort: str
) -> None:
    """Test that sort orders TMDB already understands are forwarded unchanged."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(json=EMPTY_DISCOVER_RESPONSE)

    service = TMDBService()
    await service.get_media(media_type=media_type, sort_by=requested_sort)

    request = httpx_mock.get_requests()[0]
    assert f"sort_by={requested_sort}" in str(request.url)


def test_get_media_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        service = TMDBService()

    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_media_raises_value_error_for_unsupported_media_type(monkeypatch):
    """Test that ValueError is raised for unsupported media types."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    with pytest.raises(ValueError) as exc_info:
        await service.get_media(media_type="unsupported_type")

    assert "Unsupported media type" in str(exc_info.value)
    assert "unsupported_type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_media_raises_api_response_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        status_code=401,
        text="Invalid API key"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_media_raises_api_response_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        content=b"Not valid JSON!"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_media_raises_api_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url=build_discover_url("movie")
    )

    service = TMDBService()

    with pytest.raises(APIConnectionError) as exc_info:
        await service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "Failed to connect to TMDB API" in str(exc_info.value)
