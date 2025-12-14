"""Integration tests for greenroom tools."""

import pytest
from pytest_httpx import HTTPXMock

from greenroom.tools.discovery_tools import discover_films_from_tmdb, discover_tv_shows_from_tmdb
from greenroom.tools.fetching_tools import fetch_genres


def test_discover_films_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Integration test: Use genre ID from list_genres with discover_films."""
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

    # Mock discover_films response
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

    # Use genre ID to discover films
    result = discover_films_from_tmdb(genre_id=action_id)

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Action Film"
    assert action_id in result["results"][0]["genre_ids"]

def test_discover_tv_shows_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Integration test: Use genre ID from list_genres with discover_tv_shows."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response
    genre_response = {"genres": [{"id": 18, "name": "Drama"}]}

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json={"genres": []}
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=genre_response
    )

    # Get genre ID from list_genres
    genres = fetch_genres()
    drama_id = genres["Drama"]["id"]

    assert drama_id == 18

    # Mock discover_tv_shows response
    discovery_response = {
        "page": 1,
        "total_results": 50,
        "total_pages": 3,
        "results": [
            {"id": 1396, "name": "Breaking Bad", "genre_ids": [18], "vote_average": 8.9}
        ]
    }

    httpx_mock.add_response(
        url=f"https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres={drama_id}",
        json=discovery_response
    )

    # Use genre ID to discover TV shows
    result = discover_tv_shows_from_tmdb(genre_id=drama_id)

    assert len(result["results"]) == 1
    assert result["results"][0]["name"] == "Breaking Bad"
    assert drama_id in result["results"][0]["genre_ids"]
