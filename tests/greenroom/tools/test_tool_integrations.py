"""Integration tests for greenroom tools."""

import pytest
from pytest_httpx import HTTPXMock

from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media_types import MEDIA_TYPE_FILM
from greenroom.tools.fetching_tools import fetch_genres


def test_discover_films_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Integration test: Use genre ID from list_genres with discover."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response
    genre_response = {
        "genres": [{"id": 28, "name": "Action"}]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=genre_response
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json={"genres": []}
    )

    # Get genre ID from list_genres
    genres = fetch_genres()
    action_id = genres["Action"]["id"]

    assert action_id == 28

    # Mock discover response
    discovery_response = {
        "page": 1,
        "total_results": 50,
        "total_pages": 3,
        "results": [
            {"id": 1, "title": "Action Film", "genre_ids": [28], "vote_average": 7.5}
        ]
    }

    httpx_mock.add_response(
        url=f"https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres={action_id}",
        json=discovery_response
    )

    # Use genre ID to discover films via service
    service = TMDBService()
    result = service.discover(media_type=MEDIA_TYPE_FILM, genre_id=action_id)

    assert len(result.results) == 1
    assert result.results[0].title == "Action Film"
    assert action_id in result.results[0].genre_ids
