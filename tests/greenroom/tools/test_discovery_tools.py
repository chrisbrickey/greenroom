"""Tests for discovery_tools.py tool layer."""

import pytest
from datetime import date

from greenroom.tools.discovery_tools import (
    _validate_discovery_params_internal,
    _format_media_list
)
from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION


def test_validate_discovery_params_internal_rejects_invalid_year():
    """Test parameter validation rejects invalid year."""
    with pytest.raises(ValueError, match="year must be 1900 or later"):
        _validate_discovery_params_internal(MEDIA_TYPE_FILM, 1899, 1, 20, None, None)


def test_validate_discovery_params_internal_rejects_invalid_page():
    """Test parameter validation rejects invalid page."""
    with pytest.raises(ValueError, match="page must be 1 or greater"):
        _validate_discovery_params_internal(MEDIA_TYPE_FILM, None, 0, 20, None, None)


def test_validate_discovery_params_internal_rejects_invalid_max_results():
    """Test parameter validation rejects invalid max_results."""
    with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
        _validate_discovery_params_internal(MEDIA_TYPE_FILM, None, 1, 150, None, None)

    with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
        _validate_discovery_params_internal(MEDIA_TYPE_FILM, None, 1, 0, None, None)


def test_validate_discovery_params_internal_accepts_valid_inputs():
    """Test parameter validation accepts valid inputs."""
    # Should not raise any exceptions
    _validate_discovery_params_internal(MEDIA_TYPE_FILM, 2024, 1, 20, "en", "popularity.desc")
    _validate_discovery_params_internal(MEDIA_TYPE_FILM, None, 2, 50, None, "vote_average.desc")
    _validate_discovery_params_internal(MEDIA_TYPE_FILM, 1900, 10, 100, "fr", "date.asc")


def test_validate_discovery_params_internal_accepts_television_media_type():
    """Test parameter validation accepts television media type."""
    # Should not raise any exceptions
    _validate_discovery_params_internal(MEDIA_TYPE_TELEVISION, 2024, 1, 20, "en", "popularity.desc")
    _validate_discovery_params_internal(MEDIA_TYPE_TELEVISION, None, 2, 50, None, "vote_average.desc")


def test_format_media_list_formats_correctly(monkeypatch):
    """Test that _format_media_list creates correct output structure."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    media_items = [
        Media(id="1", media_type=MEDIA_TYPE_FILM, title="Film 1", date=date(2024, 1, 15), rating=8.0, description="Description 1", genre_ids=[28]),
        Media(id="2", media_type=MEDIA_TYPE_FILM, title="Film 2", date=None, rating=None, description=None, genre_ids=[]),
    ]

    media_list = MediaList(
        results=media_items,
        total_results=50,
        page=1,
        total_pages=3
    )

    service = TMDBService()
    result = _format_media_list(media_list, service)

    assert result["page"] == 1
    assert result["total_results"] == 50
    assert result["total_pages"] == 3
    assert result["provider"] == "TMDB"
    assert len(result["results"]) == 2

    # Check first result
    assert result["results"][0]["id"] == "1"
    assert result["results"][0]["media_type"] == MEDIA_TYPE_FILM
    assert result["results"][0]["title"] == "Film 1"
    assert result["results"][0]["date"] == "2024-01-15"
    assert result["results"][0]["rating"] == 8.0
    assert result["results"][0]["description"] == "Description 1"
    assert result["results"][0]["genre_ids"] == [28]

    # Check second result with None values
    assert result["results"][1]["id"] == "2"
    assert result["results"][1]["title"] == "Film 2"
    assert result["results"][1]["date"] is None
    assert result["results"][1]["rating"] is None
    assert result["results"][1]["description"] is None
    assert result["results"][1]["genre_ids"] == []


def test_format_media_list_formats_television_correctly(monkeypatch):
    """Test that _format_media_list creates correct output for television shows."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    media_items = [
        Media(id="1", media_type=MEDIA_TYPE_TELEVISION, title="Television Show 1", date=date(2024, 1, 15), rating=8.0, description="Description 1", genre_ids=[18]),
        Media(id="2", media_type=MEDIA_TYPE_TELEVISION, title="Television Show 2", date=None, rating=None, description=None, genre_ids=[]),
    ]

    media_list = MediaList(
        results=media_items,
        total_results=50,
        page=1,
        total_pages=3
    )

    service = TMDBService()
    result = _format_media_list(media_list, service)

    assert result["page"] == 1
    assert result["total_results"] == 50
    assert result["total_pages"] == 3
    assert result["provider"] == "TMDB"
    assert len(result["results"]) == 2
    assert result["results"][0]["media_type"] == MEDIA_TYPE_TELEVISION
