"""Tests for TMDBService.search_media()."""

from datetime import date
from typing import Any
from urllib.parse import quote, urlencode

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE, SEARCH_MAX_RESULTS
from greenroom.services.tmdb.service import TMDBService

from .conftest import (
    TEST_API_KEY,
    TMDB_BASE_URL,
    TRUNCATED_MAX_RESULTS,
    SampleMedia,
    build_oversized_page,
)

FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"
UNMATCHED_QUERY = "No Such Title"

# Stated separately because tests other than the mapping ones borrow just the title
FILM_TITLE = "Test Film One"

# Entries on the sample result pages. Each holds only what the mapper copies
# verbatim, so the mocked payload and the expected Media can share it.
FILM_ONE = SampleMedia(
    title=FILM_TITLE,
    description="Sample description for the first sample film.",
    rating=8.2,
    genre_ids=[28, 878],
)
FILM_TWO = SampleMedia(
    title="Test Film Two",
    description="Sample description for the second sample film.",
    rating=7.0,
    genre_ids=[28, 12, 878],
)
TELEVISION_ONE = SampleMedia(
    title="Test Show One",
    description="Sample description for the sample television show.",
    rating=8.4,
    genre_ids=[18, 9648, 878],
)


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


def build_empty_response(page: int = 1) -> dict[str, Any]:
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
                "title": FILM_ONE.title,
                "release_date": "1999-03-30",
                "vote_average": FILM_ONE.rating,
                "overview": FILM_ONE.description,
                "genre_ids": FILM_ONE.genre_ids
            },
            {
                "id": 602,
                "title": FILM_TWO.title,
                "release_date": "2003-05-15",
                "vote_average": FILM_TWO.rating,
                "overview": FILM_TWO.description,
                "genre_ids": FILM_TWO.genre_ids
            }
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    # Compared whole, so a field this test forgot to name cannot drift unnoticed.
    assert result == MediaList(
        page=1,
        total_results=3,
        total_pages=1,
        results=[
            Media(
                id="601",
                media_type=MEDIA_TYPE_FILM,
                title=FILM_ONE.title,
                date=date(1999, 3, 30),
                rating=FILM_ONE.rating,
                description=FILM_ONE.description,
                genre_ids=FILM_ONE.genre_ids,
            ),
            Media(
                id="602",
                media_type=MEDIA_TYPE_FILM,
                title=FILM_TWO.title,
                date=date(2003, 5, 15),
                rating=FILM_TWO.rating,
                description=FILM_TWO.description,
                genre_ids=FILM_TWO.genre_ids,
            ),
        ],
    )


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
                "name": TELEVISION_ONE.title,
                "first_air_date": "2022-02-17",
                "vote_average": TELEVISION_ONE.rating,
                "overview": TELEVISION_ONE.description,
                "genre_ids": TELEVISION_ONE.genre_ids
            }
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("tv", TELEVISION_QUERY),
        json=mock_response
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_TELEVISION, query=TELEVISION_QUERY)

    # Compared whole, so a field this test forgot to name cannot drift unnoticed.
    assert result == MediaList(
        page=1,
        total_results=1,
        total_pages=1,
        results=[
            Media(
                id="701",
                media_type=MEDIA_TYPE_TELEVISION,
                title=TELEVISION_ONE.title,
                date=date(2022, 2, 17),
                rating=TELEVISION_ONE.rating,
                description=TELEVISION_ONE.description,
                genre_ids=TELEVISION_ONE.genre_ids,
            ),
        ],
    )


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

    returned_count = SEARCH_MAX_RESULTS + 5
    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=build_oversized_page(returned_count)
    )

    service = TMDBService()
    result = await service.search_media(
        media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, max_results=TRUNCATED_MAX_RESULTS
    )

    assert len(result.results) == TRUNCATED_MAX_RESULTS
    # total_results still reflects what TMDB reported, not the truncated count
    assert result.total_results == returned_count


@pytest.mark.asyncio
async def test_search_media_applies_search_max_results_by_default(monkeypatch, httpx_mock: HTTPXMock):
    """Test that omitting max_results truncates to the search default.

    The default is what an agent gets when it does not ask for a count, so a
    signature that drifted from media_limits would quietly change every
    unqualified call.
    """
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=build_oversized_page(SEARCH_MAX_RESULTS + 5)
    )

    service = TMDBService()
    result = await service.search_media(media_type=MEDIA_TYPE_FILM, query=FILM_QUERY)

    assert len(result.results) == SEARCH_MAX_RESULTS


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
            {"id": 2, "title": "Missing Date Film"},  # No release_date
            {"id": 1},  # Only ID
            {"id": 4, "title": FILM_TITLE, "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Sample description", "genre_ids": [28]},
            {"id": 3, "vote_average": 6.0},  # No title
            {"title": "No ID Film"},  # Missing ID - should be filtered out
            {"id": 5, "title": "Invalid Date Film", "release_date": "not-a-date"},  # Invalid date format
        ]
    }

    httpx_mock.add_response(
        url=build_search_url("movie", FILM_QUERY),
        json=mock_response
    )

    service = TMDBService()

    # IMPORTANT: max_results must be passed explicitly in this test to ensure
    # that the default value for that field is not the source of truncation/filtering.
    # If we don't override max_results here and the default value (e.g., SEARCH_MAX_RESULTS)
    # happens to be smaller than the set of mocked results, then this test
    # would pass whether or not a malformed entry was actually filtered out.
    result = await service.search_media(
        media_type=MEDIA_TYPE_FILM, query=FILM_QUERY, max_results=PROVIDER_PAGE_SIZE
    )

    # Keyed by id rather than position, so reordering the mock above does not
    # disturb the expectations below. This test is about how each malformed
    # entry is mapped, not about the order the provider returned them in.
    by_id = {media.id: media for media in result.results}

    # The entry with no id is dropped rather than failing the whole page
    assert set(by_id) == {"1", "2", "3", "4", "5"}

    # Compared whole, so a field this test forgot to name cannot drift unnoticed
    assert by_id["4"] == Media(
        id="4",
        media_type=MEDIA_TYPE_FILM,
        title=FILM_TITLE,
        date=date(2024, 1, 1),
        rating=7.5,
        description="Sample description",
        genre_ids=[28],
    )

    # Absent fields fall back instead of raising: title to "", the rest to
    # None, and genre_ids to an empty list
    assert by_id["2"] == Media(
        id="2", media_type=MEDIA_TYPE_FILM, title="Missing Date Film", genre_ids=[]
    )
    assert by_id["1"] == Media(
        id="1", media_type=MEDIA_TYPE_FILM, title="", genre_ids=[]
    )
    assert by_id["3"] == Media(
        id="3", media_type=MEDIA_TYPE_FILM, title="", rating=6.0, genre_ids=[]
    )

    # An unparseable date is treated as absent rather than propagated
    assert by_id["5"] == Media(
        id="5", media_type=MEDIA_TYPE_FILM, title="Invalid Date Film", genre_ids=[]
    )


@pytest.mark.asyncio
async def test_search_media_returns_empty_list_for_unmatched_query(monkeypatch, httpx_mock: HTTPXMock):
    """Test a query the provider matches nothing to comes back as an empty MediaList.

    No matches is a normal answer rather than an error, so it must reach the
    caller as an empty result set.
    """
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    httpx_mock.add_response(
        url=build_search_url("movie", UNMATCHED_QUERY),
        json=build_empty_response()
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
