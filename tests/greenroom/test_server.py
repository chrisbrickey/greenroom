"""Tests for server.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.config import Mood
from greenroom.server import (
    fetch_genres,
    simplify_genres,
    categorize_all_genres,
    _categorize_single_genre,
)


# Shared test data for simplify_genres tests
SAMPLE_GENRES = {
    "Action": {"id": 28, "has_movies": True, "has_tv_shows": False},
    "Drama": {"id": 18, "has_movies": True, "has_tv_shows": True},
    "Mystery": {"id": 9648, "has_movies": False, "has_tv_shows": True},
}


def test_fetch_genres_combines_media_types(monkeypatch, httpx_mock: HTTPXMock):
    """Test list_genres returns combined movie and TV genres."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API responses
    movie_genres = {
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
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=movie_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    # Call the function
    result = fetch_genres()

    # Expected result structure
    expected = {
        "Drama": {
            "id": 18,
            "has_movies": True,
            "has_tv_shows": True
        },
        "Action": {
            "id": 28,
            "has_movies": True,
            "has_tv_shows": False
        },
        "Mystery": {
            "id": 9648,
            "has_movies": False,
            "has_tv_shows": True
        }
    }

    # Single assertion comparing entire structure
    assert result == expected


def test_fetch_genres_drops_incomplete_genre_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that genres with missing id or name fields are silently dropped."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API responses with incomplete data
    movie_genres = {
        "genres": [
            {"id": 28, "name": "Action"},  # Valid
            {"id": 18},  # Missing name - should be dropped
            {"name": "Comedy"},  # Missing id - should be dropped
            {"id": 12, "name": "Adventure"},  # Valid
        ]
    }

    tv_genres = {
        "genres": [
            {"id": 18, "name": "Drama"},  # Valid
            {},  # Missing both - should be dropped
            {"id": 9648, "name": "Mystery"},  # Valid
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=movie_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    # Call the function
    result = fetch_genres()

    # Expected result should only include valid genres
    expected = {
        "Action": {
            "id": 28,
            "has_movies": True,
            "has_tv_shows": False
        },
        "Adventure": {
            "id": 12,
            "has_movies": True,
            "has_tv_shows": False
        },
        "Drama": {
            "id": 18,
            "has_movies": False,
            "has_tv_shows": True
        },
        "Mystery": {
            "id": 9648,
            "has_movies": False,
            "has_tv_shows": True
        }
    }

    assert result == expected


def test_fetch_genres_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    # Ensure TMDB_API_KEY is not set
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    # Call the function and expect ValueError
    with pytest.raises(ValueError) as exc_info:
        fetch_genres()

    # Verify the error message mentions the API key
    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_fetch_genres_raises_runtime_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns HTTP error."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to return 401 Unauthorized error
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        status_code=401,
        text="Invalid API key"
    )

    # Call the function and expect RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        fetch_genres()

    # Verify the error message mentions the HTTP error
    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_fetch_genres_raises_runtime_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns invalid JSON."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to return invalid JSON for movie endpoint
    # (Both endpoints need to be mocked since fetch_genres calls both)
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        content=b"This is not valid JSON at all!"
    )

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json={"genres": []}  # Valid response for TV endpoint
    )

    # Call the function and expect RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        fetch_genres()

    # Verify the error message mentions invalid JSON
    assert "invalid JSON" in str(exc_info.value)


def test_fetch_genres_raises_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that ConnectionError is raised when unable to connect to TMDB API."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to raise a connection error
    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key"
    )

    # Call the function and expect ConnectionError
    with pytest.raises(ConnectionError) as exc_info:
        fetch_genres()

    # Verify the error message mentions connection failure
    assert "Failed to connect to TMDB API" in str(exc_info.value)


@pytest.mark.asyncio
@patch("greenroom.server.fetch_genres")
async def test_list_genres_simplified_calls_sample_with_correct_prompt(mock_fetch_genres):
    """Test that simplify_genres calls ctx.sample with the genre data."""
    mock_fetch_genres.return_value = SAMPLE_GENRES

    # Create mock Context with async sample method
    mock_ctx, mock_response = MagicMock(), MagicMock()
    mock_response.text = "Action, Drama, Mystery"
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    # Call the function
    result = await simplify_genres(mock_ctx)

    # Verify ctx.sample was called with exact expected arguments
    mock_ctx.sample.assert_called_once_with(
        messages=f"Extract just the genre names from this data and return as a simple sorted comma-separated list:\n{SAMPLE_GENRES}",
        system_prompt="You are a data formatter. Return only a clean, sorted list of genre names, nothing else.",
        temperature=0.0,
        max_tokens=500
    )

    # Verify the result is the response text
    assert result == "Action, Drama, Mystery"


@pytest.mark.asyncio
@patch("greenroom.server.fetch_genres")
async def test_list_genres_simplified_falls_back_on_sample_failure(mock_fetch_genres):
    """Test that simplify_genres falls back to sorted keys when sampling fails."""
    mock_fetch_genres.return_value = SAMPLE_GENRES

    # Create mock Context where sample raises an exception
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Sampling not supported"))
    mock_ctx.warning = AsyncMock()

    # Call the function
    result = await simplify_genres(mock_ctx)

    # Verify fallback returns sorted genre names
    assert result == "Action, Drama, Mystery"

    # Verify warning was logged
    mock_ctx.warning.assert_called_once()
    warning_msg = mock_ctx.warning.call_args[0][0]
    assert "Sampling failed" in warning_msg
    assert "RuntimeError" in warning_msg


@pytest.mark.asyncio
@patch("greenroom.server.fetch_genres")
async def test_categorize_all_genres_groups_genres_by_mood(mock_fetch_genres):
    """Test that categorize_all_genres correctly groups genres using hardcoded mappings."""
    # Mock genre data with known genres from the hardcoded mapping
    mock_fetch_genres.return_value = {
        "Horror": {"id": 27, "has_movies": True, "has_tv_shows": False},
        "Comedy": {"id": 35, "has_movies": True, "has_tv_shows": True},
        "Documentary": {"id": 99, "has_movies": True, "has_tv_shows": True},
        "Action": {"id": 28, "has_movies": True, "has_tv_shows": False},
        "Thriller": {"id": 53, "has_movies": True, "has_tv_shows": False},
        "Family": {"id": 10751, "has_movies": True, "has_tv_shows": False},
    }

    # Create mock Context (not needed for hardcoded mappings but required by signature)
    mock_ctx = MagicMock()

    # Call the function
    result = await categorize_all_genres(mock_ctx)

    # Verify correct categorization
    expected = {
        Mood.DARK.value: ["Horror", "Thriller"],
        Mood.LIGHT.value: ["Comedy", "Family"],
        Mood.SERIOUS.value: ["Documentary"],
        Mood.FUN.value: ["Action"],
        Mood.OTHER.value: []
    }

    assert result == expected


@pytest.mark.asyncio
async def test_categorize_single_genre_uses_hardcoded_mapping():
    """Test that _categorize_single_genre returns hardcoded mood for known genres."""
    # Create mock Context (not needed for hardcoded mappings)
    mock_ctx = MagicMock()

    # Test various hardcoded genres
    assert await _categorize_single_genre("Horror", mock_ctx) == Mood.DARK.value
    assert await _categorize_single_genre("Comedy", mock_ctx) == Mood.LIGHT.value
    assert await _categorize_single_genre("Documentary", mock_ctx) == Mood.SERIOUS.value
    assert await _categorize_single_genre("Action", mock_ctx) == Mood.FUN.value


@pytest.mark.asyncio
async def test_categorize_single_genre_uses_llm_for_unknown_genres():
    """Test that _categorize_single_genre falls back to LLM for unknown genres."""
    # Create mock Context with async sample method
    mock_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Fun"
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    # Test with unknown genre
    result = await _categorize_single_genre("Western", mock_ctx)

    # Verify LLM was called
    mock_ctx.sample.assert_called_once()
    call_args = mock_ctx.sample.call_args

    # Verify the prompt includes the genre name and mood options
    assert "Western" in call_args.kwargs["messages"]
    assert "Dark, Light, Serious, or Fun" in call_args.kwargs["messages"]

    # Verify result is the LLM response
    assert result == Mood.FUN.value


@pytest.mark.asyncio
async def test_categorize_single_genre_falls_back_to_other_on_llm_failure():
    """Test that _categorize_single_genre defaults to OTHER when LLM fails."""
    # Create mock Context where sample raises an exception
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Sampling not supported"))
    mock_ctx.warning = AsyncMock()

    # Test with unknown genre
    result = await _categorize_single_genre("Unknown Genre", mock_ctx)

    # Verify fallback to OTHER
    assert result == Mood.OTHER.value

    # Verify warning was logged
    mock_ctx.warning.assert_called_once()
    warning_msg = mock_ctx.warning.call_args[0][0]
    assert "LLM categorization failed" in warning_msg
    assert "Unknown Genre" in warning_msg


@pytest.mark.asyncio
async def test_categorize_single_genre_validates_llm_response():
    """Test that _categorize_single_genre validates LLM response and falls back if invalid."""
    # Create mock Context with invalid LLM response
    mock_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "InvalidMood"  # Not one of the four valid moods
    mock_ctx.sample = AsyncMock(return_value=mock_response)
    mock_ctx.warning = AsyncMock()

    # Test with unknown genre
    result = await _categorize_single_genre("Unknown Genre", mock_ctx)

    # Verify fallback to OTHER when LLM returns invalid mood
    assert result == Mood.OTHER.value


@pytest.mark.asyncio
@patch("greenroom.server.fetch_genres")
async def test_categorize_all_genres_with_unknown_genres_uses_llm(mock_fetch_genres):
    """Test that categorize_all_genres uses LLM for all unknown genres."""
    # Mock genre data with genres NOT in GENRE_MOOD_MAP
    mock_fetch_genres.return_value = {
        "Western": {"id": 37, "has_movies": True, "has_tv_shows": False},
        "Experimental": {"id": 9999, "has_movies": True, "has_tv_shows": True},
        "Noir": {"id": 10001, "has_movies": False, "has_tv_shows": True},
    }

    # Create mock Context with sample returning different moods for each genre
    # Note: Genres are processed in sorted order: Experimental, Noir, Western
    mock_ctx = MagicMock()
    mock_responses = [
        MagicMock(text="Dark"),     # Experimental -> Dark
        MagicMock(text="Dark"),     # Noir -> Dark
        MagicMock(text="Fun"),      # Western -> Fun
    ]
    mock_ctx.sample = AsyncMock(side_effect=mock_responses)

    # Call function
    result = await categorize_all_genres(mock_ctx)

    # Verify LLM was called for each unknown genre (3 times)
    assert mock_ctx.sample.call_count == 3

    # Verify each call includes the genre name in the prompt
    call_args_list = mock_ctx.sample.call_args_list
    assert "Experimental" in call_args_list[0].kwargs["messages"]
    assert "Noir" in call_args_list[1].kwargs["messages"]
    assert "Western" in call_args_list[2].kwargs["messages"]

    # Verify genres are categorized according to LLM responses
    expected = {
        Mood.DARK.value: ["Experimental", "Noir"],
        Mood.LIGHT.value: [],
        Mood.SERIOUS.value: [],
        Mood.FUN.value: ["Western"],
        Mood.OTHER.value: []
    }
    assert result == expected


@pytest.mark.asyncio
@patch("greenroom.server.fetch_genres")
async def test_categorize_all_genres_falls_back_to_other_when_llm_fails(mock_fetch_genres):
    """Test that categorize_all_genres places unknown genres in Other when LLM fails."""
    # Mock genre data with genres NOT in GENRE_MOOD_MAP
    mock_fetch_genres.return_value = {
        "Western": {"id": 37, "has_movies": True, "has_tv_shows": False},
        "Experimental": {"id": 9999, "has_movies": True, "has_tv_shows": True},
    }

    # Create mock Context where sample raises exception (LLM unavailable)
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Sampling not supported"))
    mock_ctx.warning = AsyncMock()

    # Call function
    result = await categorize_all_genres(mock_ctx)

    # Verify LLM was attempted for each unknown genre
    assert mock_ctx.sample.call_count == 2

    # Verify warning was logged for each failure
    assert mock_ctx.warning.call_count == 2

    # Verify all unknown genres are placed in Other category
    expected = {
        Mood.DARK.value: [],
        Mood.LIGHT.value: [],
        Mood.SERIOUS.value: [],
        Mood.FUN.value: [],
        Mood.OTHER.value: ["Experimental", "Western"]
    }
    assert result == expected
