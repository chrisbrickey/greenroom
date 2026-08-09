"""Tests for TMDBService.search_media()."""

import httpx
import pytest
from datetime import date
from urllib.parse import quote, urlencode
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION

from .conftest import TMDB_BASE_URL, TEST_API_KEY

# Generic queries and titles for the search_media tests
FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"
FILM_TITLE = "Test Film One"
FILM_SEQUEL_TITLE = "Test Film Two"
TELEVISION_TITLE = "Test Show One"
UNMATCHED_QUERY = "No Such Title"


def build_search_url(endpoint: str, query: str, **extra_params: object) -> str:
    """Build the TMDB search URL that the service is expected to request.

    Args:
        endpoint: TMDB endpoint segment ("movie" or "tv")
        query: Title text the service is expected to send
        extra_params: Additional expected params, and overrides for the defaults

    Returns:
        Fully encoded TMDB search URL
    """
    params: dict[str, object] = {
        "api_key": TEST_API_KEY,
        "query": query,
        "page": 1,
        "include_adult": "false",
    }
    params.update(extra_params)
    return f"{TMDB_BASE_URL}/search/{endpoint}?{urlencode(params, quote_via=quote)}"


def build_empty_response(page: int = 1) -> dict:
    """Build a well-formed TMDB response carrying no results.

    Args:
        page: Page number the response reports

    Returns:
        Dictionary shaped like an empty TMDB search response
    """
    return {"page": page, "total_results": 0, "total_pages": 0, "results": []}


@pytest.mark.asyncio
async def test_search_media_returns_media_list_for_films(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media returns properly formatted MediaList for films."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mock_response = {
        "page": 1,
        "total_results": 3,
        "total_pages": 1,
        "results": [
            {
                "id": 601,
                "title": FILM_TITLE,
                "release_date": "1999-03-30",
                "vote_average": 8.2,
                "overview": "Sample description for the first sample film.",
                "genre_ids": [28, 878]
            },
            {
                "id": 602,
                "title": FILM_SEQUEL_TITLE,
                "release_date": "2003-05-15",
                "vote_average": 7.0,
                "overview": "Sample description for the second sample film.",
                "genre_ids": [28, 12, 878]
            }
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert result.page == 1
    assert result.total_results == 3
    assert result.total_pages == 1
    assert len(result.results) == 2

    # ids are coerced to strings and dates parsed into date objects
    assert result.results[0].id == "601"
    assert result.results[0].title == FILM_TITLE
    assert result.results[0].date == date(1999, 3, 30)
    assert result.results[0].rating == 8.2
    assert result.results[0].genre_ids == [28, 878]
    assert result.results[0].media_type == MEDIA_TYPE_FILM
    assert result.results[1].title == FILM_SEQUEL_TITLE


@pytest.mark.asyncio
async def test_search_media_returns_media_list_for_television(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media maps TV name/first_air_date onto the standard fields."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {
                "id": 701,
                "name": TELEVISION_TITLE,
                "first_air_date": "2022-02-17",
                "vote_average": 8.4,
                "overview": "Sample description for the sample television show.",
                "genre_ids": [18, 9648, 878]
            }
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("tv", TELEVISION_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_TELEVISION, query=TELEVISION_QUERY)

    assert len(result.results) == 1
    assert result.results[0].id == "701"
    assert result.results[0].title == TELEVISION_TITLE
    assert result.results[0].date == date(2022, 2, 17)
    assert result.results[0].media_type == MEDIA_TYPE_TELEVISION


@pytest.mark.asyncio
async def test_search_media_sends_query_and_defaults(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media sends the query verbatim with default params and no discover-only params."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=build_empty_response()
    )

    service = TMDBService()
    await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert len(httpx_mock.get_requests()) == 1
    params = httpx_mock.get_requests()[0].url.params
    assert params["query"] == FILM_QUERY
    assert params["page"] == "1"
    assert params["include_adult"] == "false"

    # Search does not support the discover-only parameters
    assert "sort_by" not in params
    assert "include_video" not in params


@pytest.mark.asyncio
async def test_search_media_uses_film_year_param(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media maps year onto primary_release_year for films."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY, primary_release_year=2003),
        json=build_empty_response()
    )

    service = TMDBService()
    await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, year=2003)

    params = httpx_mock.get_requests()[0].url.params
    assert params["primary_release_year"] == "2003"
    assert "first_air_date_year" not in params


@pytest.mark.asyncio
async def test_search_media_uses_television_year_param(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media maps year onto first_air_date_year for television."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("tv", TELEVISION_QUERY, first_air_date_year=2022),
        json=build_empty_response()
    )

    service = TMDBService()
    await service.search_media(media_type=MEDIA_TYPE_TELEVISION, query=TELEVISION_QUERY, year=2022)

    params = httpx_mock.get_requests()[0].url.params
    assert params["first_air_date_year"] == "2022"
    assert "primary_release_year" not in params


@pytest.mark.asyncio
async def test_search_media_language_selects_display_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test language is sent as the display language, not as an original-language filter."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY, language="es"),
        json=build_empty_response()
    )

    service = TMDBService()
    await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, display_language="es")

    params = httpx_mock.get_requests()[0].url.params
    assert params["language"] == "es"
    assert "with_original_language" not in params


@pytest.mark.asyncio
async def test_search_media_limits_results_to_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media truncates the result list to max_results."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mock_response = {
        "page": 1,
        "total_results": 5,
        "total_pages": 1,
        "results": [
            {"id": index, "title": f"Test Film {index}", "release_date": "2020-01-01"}
            for index in range(1, 6)
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, max_results=2)

    assert len(result.results) == 2
    # total_results still reflects what TMDB reported, not the truncated count
    assert result.total_results == 5


@pytest.mark.asyncio
async def test_search_media_requests_and_reports_page(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media forwards the requested page and reports it back."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mock_response = {
        "page": 3,
        "total_results": 60,
        "total_pages": 3,
        "results": [
            {"id": 610, "title": FILM_TITLE, "release_date": "2020-01-01"}
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY, page=3),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, page=3)

    assert httpx_mock.get_requests()[0].url.params["page"] == "3"
    assert result.page == 3
    assert result.total_pages == 3
    assert result.total_results == 60


@pytest.mark.asyncio
async def test_search_media_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that search results with missing or malformed fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mock_response = {
        "page": 1,
        "total_results": 6,
        "total_pages": 1,
        "results": [
            {"id": 1, "title": FILM_TITLE, "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Sample description", "genre_ids": [28]},
            {"id": 2, "title": "Missing Date Film"},  # No release_date
            {"id": 3, "vote_average": 6.0},  # No title
            {"id": 4},  # Only ID
            {"id": 5, "title": "Invalid Date Film", "release_date": "not-a-date"},  # Invalid date format
            {"title": "No ID Film"},  # Missing ID - should be filtered out
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    # Should return 5 media items (all with IDs), not 6
    assert len(result.results) == 5

    # Check first item has all data
    assert result.results[0].title == FILM_TITLE
    assert result.results[0].date == date(2024, 1, 1)
    assert result.results[0].rating == 7.5
    assert result.results[0].description == "Sample description"
    assert result.results[0].genre_ids == [28]

    # Check that missing fields are None or empty
    assert result.results[1].title == "Missing Date Film"
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
async def test_search_media_handles_missing_results_key(monkeypatch, httpx_mock: HTTPXMock):
    """Test search_media returns an empty MediaList when TMDB omits the results key."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", UNMATCHED_QUERY),
        json={"page": 1}
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=UNMATCHED_QUERY)

    assert result.results == []
    assert result.total_results == 0
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_search_media_raises_value_error_for_unsupported_media_type(monkeypatch):
    """Test that ValueError is raised for unsupported media types."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    service = TMDBService()

    with pytest.raises(ValueError) as exc_info:
        await service.search_media(media_type="unsupported_type", query=FILM_QUERY)

    assert "Unsupported media type" in str(exc_info.value)
    assert "unsupported_type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_media_raises_api_response_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        status_code=401,
        text="Invalid API key"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_media_raises_api_response_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        content=b"Not valid JSON!"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert "invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_media_raises_api_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url=build_search_url("movie", FILM_QUERY)
    )

    service = TMDBService()

    with pytest.raises(APIConnectionError) as exc_info:
        await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert "Failed to connect to TMDB API" in str(exc_info.value)
