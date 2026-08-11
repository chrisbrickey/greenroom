"""Tests for TMDBService.get_genres()."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.services.tmdb.service import TMDBService

from .conftest import TMDB_BASE_URL, TEST_API_KEY

# Genre endpoints take no query params beyond the API key, so they're static
FILM_GENRE_URL = f"{TMDB_BASE_URL}/genre/movie/list?api_key={TEST_API_KEY}"
TELEVISION_GENRE_URL = f"{TMDB_BASE_URL}/genre/tv/list?api_key={TEST_API_KEY}"


@pytest.mark.asyncio
async def test_get_genres_combines_film_and_tv_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_genres returns combined film and TV genres with correct flags."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    film_genres = {
        "genres": [
            {"id": 28, "name": "Action"},
            {"id": 18, "name": "Drama"},
        ]
    }

    tv_genres = {
        "genres": [
            {"id": 18, "name": "Drama"},
            {"id": 9648, "name": "Mystery"},
        ]
    }

    httpx_mock.add_response(
        url=FILM_GENRE_URL,
        json=film_genres
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json=tv_genres
    )

    service = TMDBService()
    result = await service.get_genres()

    # Should return GenreList with 3 unique genres
    assert len(result.genres) == 3

    # Convert to dict for easier assertions
    genres_by_name = {g.name: g for g in result.genres}

    # Action is film-only
    assert genres_by_name["Action"].id == 28
    assert genres_by_name["Action"].has_films is True
    assert genres_by_name["Action"].has_tv_shows is False

    # Drama is both film and TV
    assert genres_by_name["Drama"].id == 18
    assert genres_by_name["Drama"].has_films is True
    assert genres_by_name["Drama"].has_tv_shows is True

    # Mystery is TV-only
    assert genres_by_name["Mystery"].id == 9648
    assert genres_by_name["Mystery"].has_films is False
    assert genres_by_name["Mystery"].has_tv_shows is True


@pytest.mark.asyncio
async def test_get_genres_drops_incomplete_genre_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that genres with missing id or name fields are silently dropped."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    film_genres = {
        "genres": [
            {"id": 28, "name": "Action"},  # Valid
            {"id": 18},  # Missing name - should be dropped
            {"name": "Comedy"},  # Missing id - should be dropped
        ]
    }

    tv_genres = {
        "genres": [
            {"id": 9648, "name": "Mystery"},  # Valid
            {},  # Missing both - should be dropped
        ]
    }

    httpx_mock.add_response(
        url=FILM_GENRE_URL,
        json=film_genres
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json=tv_genres
    )

    service = TMDBService()
    result = await service.get_genres()

    # Should only include valid genres
    assert len(result.genres) == 2
    genre_names = {g.name for g in result.genres}
    assert genre_names == {"Action", "Mystery"}


@pytest.mark.asyncio
async def test_get_genres_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_genres handles empty genre lists gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=FILM_GENRE_URL,
        json={"genres": []}
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json={"genres": []}
    )

    service = TMDBService()
    result = await service.get_genres()

    assert result.genres == []


@pytest.mark.asyncio
async def test_get_genres_raises_api_response_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=FILM_GENRE_URL,
        status_code=401,
        text="Invalid API key"
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json={"genres": []}
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.get_genres()

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_genres_raises_api_response_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url=FILM_GENRE_URL,
        content=b"Not valid JSON!"
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json={"genres": []}
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        await service.get_genres()

    assert "invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_genres_raises_api_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url=FILM_GENRE_URL
    )
    httpx_mock.add_response(
        url=TELEVISION_GENRE_URL,
        json={"genres": []}
    )

    service = TMDBService()

    with pytest.raises(APIConnectionError) as exc_info:
        await service.get_genres()

    assert "Failed to connect to TMDB API" in str(exc_info.value)
