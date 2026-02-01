"""Integration tests for greenroom tools."""

import pytest
from pytest_httpx import HTTPXMock

from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.tools.genre_tools.fetching import fetch_genres


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


def test_discover_television_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Integration test: Use genre ID from list_genres with television discovery."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response with Drama genre available for both films and TV
    genre_response = {
        "genres": [{"id": 18, "name": "Drama"}]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=genre_response
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=genre_response
    )

    # Get genre ID from list_genres
    genres = fetch_genres()
    drama_id = genres["Drama"]["id"]

    assert drama_id == 18

    # Mock discover response for TV shows
    discovery_response = {
        "page": 1,
        "total_results": 50,
        "total_pages": 3,
        "results": [
            {"id": 1, "name": "Drama Show", "genre_ids": [18], "vote_average": 8.2, "first_air_date": "2024-01-15"}
        ]
    }

    httpx_mock.add_response(
        url=f"https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres={drama_id}",
        json=discovery_response
    )

    # Use genre ID to discover television via service
    service = TMDBService()
    result = service.discover(media_type=MEDIA_TYPE_TELEVISION, genre_id=drama_id)

    assert len(result.results) == 1
    assert result.results[0].title == "Drama Show"
    assert result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert drama_id in result.results[0].genre_ids


def test_discover_films_and_television_with_shared_genre(monkeypatch, httpx_mock: HTTPXMock):
    """Integration test: Discover both films and TV shows with the same shared genre ID."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response with Drama genre available for both films and TV
    genre_response = {
        "genres": [{"id": 18, "name": "Drama"}]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=genre_response
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=genre_response
    )

    # Get shared genre ID from list_genres
    genres = fetch_genres()
    drama_id = genres["Drama"]["id"]

    assert drama_id == 18
    assert genres["Drama"]["has_films"] is True
    assert genres["Drama"]["has_tv_shows"] is True

    # Mock discover response for films
    film_discovery_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {"id": 100, "title": "Drama Film", "genre_ids": [18], "vote_average": 7.8, "release_date": "2024-03-20"}
        ]
    }

    httpx_mock.add_response(
        url=f"https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres={drama_id}",
        json=film_discovery_response
    )

    # Mock discover response for TV shows
    tv_discovery_response = {
        "page": 1,
        "total_results": 80,
        "total_pages": 4,
        "results": [
            {"id": 200, "name": "Drama Show", "genre_ids": [18], "vote_average": 8.5, "first_air_date": "2024-01-10"}
        ]
    }

    httpx_mock.add_response(
        url=f"https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres={drama_id}",
        json=tv_discovery_response
    )

    # Discover films with the shared genre
    service = TMDBService()
    film_result = service.discover(media_type=MEDIA_TYPE_FILM, genre_id=drama_id)

    assert len(film_result.results) == 1
    assert film_result.results[0].title == "Drama Film"
    assert film_result.results[0].media_type == MEDIA_TYPE_FILM
    assert drama_id in film_result.results[0].genre_ids

    # Discover television with the same shared genre
    tv_result = service.discover(media_type=MEDIA_TYPE_TELEVISION, genre_id=drama_id)

    assert len(tv_result.results) == 1
    assert tv_result.results[0].title == "Drama Show"
    assert tv_result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert drama_id in tv_result.results[0].genre_ids

    # Verify they returned different content
    assert film_result.results[0].id != tv_result.results[0].id
    assert film_result.results[0].title != tv_result.results[0].title
