"""Tests for TMDBService.get_media()."""

import httpx
import pytest
from urllib.parse import quote, urlencode
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION

from .conftest import TMDB_BASE_URL, TEST_API_KEY

# Response body for tests that assert on the outgoing request rather than the results
EMPTY_DISCOVER_RESPONSE = {
    "page": 1,
    "total_results": 0,
    "total_pages": 0,
    "results": []
}


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
                "title": "Test Film One",
                "release_date": "2024-01-01",
                "vote_average": 7.5,
                "overview": "Sample description for the first sample film.",
                "genre_ids": [18, 53],
                "poster_path": "/path.jpg"
            },
            {
                "id": 2,
                "title": "Test Film Two",
                "release_date": "2024-02-02",
                "vote_average": 8.0,
                "overview": "Sample description for the second sample film.",
                "genre_ids": [80, 18],
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

    assert result.page == 1
    assert result.total_results == 100
    assert result.total_pages == 5
    assert len(result.results) == 2
    assert result.results[0].title == "Test Film One"
    assert result.results[0].rating == 7.5
    assert result.results[0].genre_ids == [18, 53]
    assert result.results[0].media_type == MEDIA_TYPE_FILM
    assert result.results[1].title == "Test Film Two"


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
                "name": "Test Show One",
                "first_air_date": "2024-03-03",
                "vote_average": 7.8,
                "overview": "Sample description for the first sample television show.",
                "genre_ids": [10765, 18, 10759],
            },
            {
                "id": 4,
                "name": "Test Show Two",
                "first_air_date": "2024-04-04",
                "vote_average": 8.2,
                "overview": "Sample description for the second sample television show.",
                "genre_ids": [18, 80],
            }
        ]
    }

    httpx_mock.add_response(
        url=build_discover_url("tv", with_genres=18, first_air_date_year=2024),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_TELEVISION, genre_id=18, year=2024, page=1)

    assert result.page == 1
    assert result.total_results == 50
    assert result.total_pages == 3
    assert len(result.results) == 2
    assert result.results[0].title == "Test Show One"
    assert result.results[0].rating == 7.8
    assert result.results[0].genre_ids == [10765, 18, 10759]
    assert result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert result.results[0].date.isoformat() == "2024-03-03"
    assert result.results[1].title == "Test Show Two"


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
    result = await service.get_media(media_type=MEDIA_TYPE_FILM)

    # Should return 5 media items (all with IDs), not 6
    assert len(result.results) == 5

    # Check first item has all data
    assert result.results[0].title == "Complete Film"
    assert result.results[0].date.isoformat() == "2024-01-01"
    assert result.results[0].rating == 7.5
    assert result.results[0].description == "Full details"
    assert result.results[0].genre_ids == [28]

    # Check that missing fields are None or empty
    assert result.results[1].title == "Missing Date"
    assert result.results[1].date is None
    assert result.results[1].description is None

    assert result.results[2].title == ""  # Empty string for missing title
    assert result.results[2].rating == 6.0

    # Check item with only ID
    assert result.results[3].id == "4"
    assert result.results[3].title == ""
    assert result.results[3].genre_ids == []

    # Check item with invalid date format - date should be None
    assert result.results[4].id == "5"
    assert result.results[4].title == "Invalid Date Film"
    assert result.results[4].date is None


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
async def test_get_media_respects_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test that max_results parameter limits returned media."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock response with 20 films
    mock_results = [{"id": i, "title": f"Film {i}"} for i in range(20)]
    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": mock_results
    }

    httpx_mock.add_response(
        url=build_discover_url("movie"),
        json=mock_response
    )

    service = TMDBService()
    result = await service.get_media(media_type=MEDIA_TYPE_FILM, max_results=5)

    assert len(result.results) == 5
    assert result.results[0].id == "0"
    assert result.results[4].id == "4"


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
async def test_get_media_filters_by_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test language parameter filters media correctly."""
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
    result = await service.get_media(media_type=MEDIA_TYPE_FILM, language="es")

    assert len(result.results) == 1
    assert result.results[0].title == "Spanish Film"

    # Verify the URL included the language parameter
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
