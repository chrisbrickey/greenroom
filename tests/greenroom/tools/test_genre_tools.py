"""Tests for genre tools. Service-level behavior is mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from greenroom.tools.genre_tools import (
    fetch_genres,
    simplify_genres,
    categorize_all_genres,
)
from greenroom.models.genre import Genre, GenreList
from greenroom.config import Mood


# =============================================================================
# Test fetch_genres()
# =============================================================================

def test_fetch_genres_transforms_genre_list_to_dict():
    """Test fetch_genres transforms GenreList to dict format correctly."""
    # Create a mock service that returns a GenreList
    mock_service = MagicMock()
    mock_service.get_genres.return_value = GenreList(genres=[
        Genre(id=28, name="Action", has_films=True, has_tv_shows=False),
        Genre(id=18, name="Drama", has_films=True, has_tv_shows=True),
        Genre(id=9648, name="Mystery", has_films=False, has_tv_shows=True),
    ])

    # Call the function with mock service
    result = fetch_genres(mock_service)

    # Expected result structure
    expected = {
        "Action": {
            "id": 28,
            "has_films": True,
            "has_tv_shows": False
        },
        "Drama": {
            "id": 18,
            "has_films": True,
            "has_tv_shows": True
        },
        "Mystery": {
            "id": 9648,
            "has_films": False,
            "has_tv_shows": True
        }
    }

    assert result == expected
    mock_service.get_genres.assert_called_once()


def test_fetch_genres_returns_empty_dict_for_empty_genre_list():
    """Test fetch_genres returns empty dict when service returns empty GenreList."""
    mock_service = MagicMock()
    mock_service.get_genres.return_value = GenreList(genres=[])

    result = fetch_genres(mock_service)

    assert result == {}
    mock_service.get_genres.assert_called_once()


def test_fetch_genres_uses_expected_keys():
    """Test fetch_genres uses expected string keys in genre property dicts."""
    mock_service = MagicMock()
    mock_service.get_genres.return_value = GenreList(genres=[
        Genre(id=99, name="Documentary", has_films=True, has_tv_shows=True),
    ])

    result = fetch_genres(mock_service)

    # Verify the keys match expected strings
    doc_props = result["Documentary"]
    assert "id" in doc_props
    assert "has_films" in doc_props
    assert "has_tv_shows" in doc_props

    # Verify the values are correct
    assert doc_props["id"] == 99
    assert doc_props["has_films"] is True
    assert doc_props["has_tv_shows"] is True


# =============================================================================
# Test simplify_genres()
# =============================================================================

# Shared test data
SAMPLE_GENRES = {
    "Action": {"id": 28, "has_films": True, "has_tv_shows": False},
    "Drama": {"id": 18, "has_films": True, "has_tv_shows": True},
    "Mystery": {"id": 9648, "has_films": False, "has_tv_shows": True},
}


@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_simplify_genres_calls_sample_with_correct_prompt(mock_fetch_genres):
    """Test that simplify_genres calls ctx.sample with the genre data."""
    mock_fetch_genres.return_value = SAMPLE_GENRES
    mock_service = MagicMock()

    # Create mock Context with async sample method
    mock_ctx, mock_response = MagicMock(), MagicMock()
    mock_response.text = "Action, Drama, Mystery"
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    # Call the function
    result = await simplify_genres(mock_ctx, mock_service)

    # Verify fetch_genres was called with the service
    mock_fetch_genres.assert_called_once_with(mock_service)

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
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_simplify_genres_falls_back_on_sample_failure(mock_fetch_genres):
    """Test that simplify_genres falls back to sorted keys when sampling fails."""
    mock_fetch_genres.return_value = SAMPLE_GENRES
    mock_service = MagicMock()

    # Create mock Context where sample raises an exception
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Sampling not supported"))
    mock_ctx.warning = AsyncMock()

    # Call the function
    result = await simplify_genres(mock_ctx, mock_service)

    # Verify fallback returns sorted genre names
    assert result == "Action, Drama, Mystery"

    # Verify warning was logged
    mock_ctx.warning.assert_called_once()
    warning_msg = mock_ctx.warning.call_args[0][0]
    assert "Sampling failed" in warning_msg
    assert "RuntimeError" in warning_msg


@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_simplify_genres_handles_empty_genres(mock_fetch_genres):
    """Test that simplify_genres handles empty genre dict."""
    mock_fetch_genres.return_value = {}
    mock_service = MagicMock()

    # Create mock Context with async sample method
    mock_ctx, mock_response = MagicMock(), MagicMock()
    mock_response.text = ""
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    # Call the function
    result = await simplify_genres(mock_ctx, mock_service)

    # Verify result is empty string from LLM
    assert result == ""


@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_simplify_genres_handles_malformed_llm_response(mock_fetch_genres):
    """Test that simplify_genres returns LLM response even if malformed."""
    mock_fetch_genres.return_value = SAMPLE_GENRES
    mock_service = MagicMock()

    # Create mock Context with malformed LLM response
    mock_ctx, mock_response = MagicMock(), MagicMock()
    mock_response.text = "Here are the genres: Action, Drama, Mystery"  # Extra text
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    result = await simplify_genres(mock_ctx, mock_service)

    # Current implementation returns LLM response as-is (no validation)
    assert result == "Here are the genres: Action, Drama, Mystery"


# =============================================================================
# Test categorize_all_genres()
# =============================================================================

@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_categorize_all_genres_groups_genres_by_mood(mock_fetch_genres):
    """Test that categorize_all_genres correctly groups genres using hardcoded mappings."""
    # Mock genre data with known genres from the hardcoded mapping
    genres_dict = {
        "Horror": {"id": 27, "has_films": True, "has_tv_shows": False},
        "Comedy": {"id": 35, "has_films": True, "has_tv_shows": True},
        "Documentary": {"id": 99, "has_films": True, "has_tv_shows": True},
        "Action": {"id": 28, "has_films": True, "has_tv_shows": False},
        "Thriller": {"id": 53, "has_films": True, "has_tv_shows": False},
        "Family": {"id": 10751, "has_films": True, "has_tv_shows": False},
    }
    mock_fetch_genres.return_value = genres_dict
    mock_service = MagicMock()

    # Create mock Context (not needed for hardcoded mappings but required by signature)
    mock_ctx = MagicMock()

    # Call the function
    result = await categorize_all_genres(mock_ctx, mock_service)

    # Verify fetch_genres was called with the service
    mock_fetch_genres.assert_called_once_with(mock_service)

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
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_categorize_all_genres_handles_empty_genres(mock_fetch_genres):
    """Test that categorize_all_genres handles empty genre dict."""
    mock_fetch_genres.return_value = {}
    mock_service = MagicMock()

    # Create mock Context
    mock_ctx = MagicMock()

    # Call the function
    result = await categorize_all_genres(mock_ctx, mock_service)

    # Verify result has all mood categories but empty lists
    expected = {
        Mood.DARK.value: [],
        Mood.LIGHT.value: [],
        Mood.SERIOUS.value: [],
        Mood.FUN.value: [],
        Mood.OTHER.value: []
    }

    assert result == expected


@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_categorize_all_genres_with_unknown_genres_uses_llm(mock_fetch_genres):
    """Test that categorize_all_genres uses LLM for all unknown genres."""
    # Mock genre data with genres NOT in GENRE_MOOD_MAP
    genres_dict = {
        "Western": {"id": 37, "has_films": True, "has_tv_shows": False},
        "Experimental": {"id": 9999, "has_films": True, "has_tv_shows": True},
        "Noir": {"id": 10001, "has_films": False, "has_tv_shows": True},
    }
    mock_fetch_genres.return_value = genres_dict
    mock_service = MagicMock()

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
    result = await categorize_all_genres(mock_ctx, mock_service)

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
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_categorize_all_genres_falls_back_to_other_when_llm_fails(mock_fetch_genres):
    """Test that categorize_all_genres places unknown genres in Other when LLM fails."""
    # Mock genre data with genres NOT in GENRE_MOOD_MAP
    genres_dict = {
        "Western": {"id": 37, "has_films": True, "has_tv_shows": False},
        "Experimental": {"id": 9999, "has_films": True, "has_tv_shows": True},
    }
    mock_fetch_genres.return_value = genres_dict
    mock_service = MagicMock()

    # Create mock Context where sample raises exception (LLM unavailable)
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Sampling not supported"))
    mock_ctx.warning = AsyncMock()

    # Call function
    result = await categorize_all_genres(mock_ctx, mock_service)

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


@pytest.mark.asyncio
@patch('greenroom.tools.genre_tools.fetch_genres')
async def test_categorize_all_genres_falls_back_to_other_on_invalid_llm_response(mock_fetch_genres):
    """Test that categorize_all_genres places genres in Other when LLM returns invalid mood."""
    # Mock genre data with unknown genre
    genres_dict = {
        "Experimental": {"id": 9999, "has_films": True, "has_tv_shows": True},
    }
    mock_fetch_genres.return_value = genres_dict
    mock_service = MagicMock()

    # Create mock Context with invalid LLM response
    mock_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "InvalidMood"  # Not one of the four valid moods
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    # Call function
    result = await categorize_all_genres(mock_ctx, mock_service)

    # Verify genre is placed in Other when LLM returns invalid mood
    expected = {
        Mood.DARK.value: [],
        Mood.LIGHT.value: [],
        Mood.SERIOUS.value: [],
        Mood.FUN.value: [],
        Mood.OTHER.value: ["Experimental"]
    }
    assert result == expected
