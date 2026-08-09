"""Integration tests for greenroom tools."""

import pytest
from pytest_httpx import HTTPXMock

from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.tools.discovery import fetch_films, find_films, find_television
from greenroom.tools.genre_tools import fetch_genres

# Generic queries and titles for the search tool integration tests
FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"
FILM_TITLE = "Test Film One"
TELEVISION_TITLE = "Test Show One"


@pytest.mark.asyncio
async def test_discover_films_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Use genre ID from genre tools to discover specific films with media discovery tools."""
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
    service = TMDBService()
    genres = await fetch_genres(service)
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
    result = await service.get_media(media_type=MEDIA_TYPE_FILM, genre_id=action_id)

    assert len(result.results) == 1
    assert result.results[0].title == "Action Film"
    assert action_id in result.results[0].genre_ids


@pytest.mark.asyncio
async def test_discover_television_with_genre_from_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Use genre ID from genre tools to discover specific tv shows with media discovery tools."""
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
    service = TMDBService()
    genres = await fetch_genres(service)
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
    result = await service.get_media(media_type=MEDIA_TYPE_TELEVISION, genre_id=drama_id)

    assert len(result.results) == 1
    assert result.results[0].title == "Drama Show"
    assert result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert drama_id in result.results[0].genre_ids


@pytest.mark.asyncio
async def test_discover_films_and_television_with_shared_genre(monkeypatch, httpx_mock: HTTPXMock):
    """Discover both films and TV shows with the same shared genre ID."""
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
    service = TMDBService()
    genres = await fetch_genres(service)
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
    film_result = await service.get_media(media_type=MEDIA_TYPE_FILM, genre_id=drama_id)

    assert len(film_result.results) == 1
    assert film_result.results[0].title == "Drama Film"
    assert film_result.results[0].media_type == MEDIA_TYPE_FILM
    assert drama_id in film_result.results[0].genre_ids

    # Discover television with the same shared genre
    tv_result = await service.get_media(media_type=MEDIA_TYPE_TELEVISION, genre_id=drama_id)

    assert len(tv_result.results) == 1
    assert tv_result.results[0].title == "Drama Show"
    assert tv_result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert drama_id in tv_result.results[0].genre_ids

    # Verify they returned different content
    assert film_result.results[0].id != tv_result.results[0].id
    assert film_result.results[0].title != tv_result.results[0].title


@pytest.mark.asyncio
async def test_search_films_returns_genre_ids_resolvable_by_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Search a film by title and resolve its genre IDs against genre tools."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response
    genre_response = {
        "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=genre_response
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json={"genres": []}
    )

    service = TMDBService()
    genres = await fetch_genres(service)

    # Mock search response
    search_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {
                "id": 601,
                "title": FILM_TITLE,
                "release_date": "1999-03-30",
                "vote_average": 8.2,
                "overview": "Sample description for the sample film.",
                "genre_ids": [28, 878]
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/search/movie?api_key=test_api_key&query=Test%20Film&page=1&include_adult=false",
        json=search_response
    )

    # Search by title through the full tool -> service -> client stack
    result = await find_films(service, FILM_QUERY)

    assert result["provider"] == "TMDB"
    assert len(result["results"]) == 1

    film = result["results"][0]
    assert film["title"] == FILM_TITLE
    assert film["date"] == "1999-03-30"
    assert film["media_type"] == MEDIA_TYPE_FILM

    # Search results carry the same genre IDs that the genre tools expose
    assert film["genre_ids"] == [genres["Action"]["id"], genres["Science Fiction"]["id"]]


@pytest.mark.asyncio
async def test_search_television_returns_genre_ids_resolvable_by_list_genres(monkeypatch, httpx_mock: HTTPXMock):
    """Search a television show by title and resolve its genre IDs against genre tools."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock list_genres response with TV-only genres
    genre_response = {
        "genres": [{"id": 18, "name": "Drama"}, {"id": 9648, "name": "Mystery"}]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json={"genres": []}
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=genre_response
    )

    service = TMDBService()
    genres = await fetch_genres(service)

    assert genres["Drama"]["has_tv_shows"] is True
    assert genres["Mystery"]["has_tv_shows"] is True

    # Mock search response
    search_response = {
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
                "genre_ids": [18, 9648]
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/search/tv?api_key=test_api_key&query=Test%20Show&page=1&include_adult=false",
        json=search_response
    )

    # Search by title through the full tool -> service -> client stack
    result = await find_television(service, TELEVISION_QUERY)

    assert result["provider"] == "TMDB"
    assert len(result["results"]) == 1

    show = result["results"][0]
    assert show["title"] == TELEVISION_TITLE
    assert show["date"] == "2022-02-17"
    assert show["media_type"] == MEDIA_TYPE_TELEVISION

    # Search results carry the same genre IDs that the genre tools expose
    assert show["genre_ids"] == [genres["Drama"]["id"], genres["Mystery"]["id"]]


@pytest.mark.asyncio
async def test_search_films_returns_same_result_shape_as_discover_films(monkeypatch, httpx_mock: HTTPXMock):
    """Search results are interchangeable with discovery results for agent consumption."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    film_payload = {
        "id": 601,
        "title": FILM_TITLE,
        "release_date": "1999-03-30",
        "vote_average": 8.2,
        "overview": "Sample description for the sample film.",
        "genre_ids": [28, 878]
    }
    response_body = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [film_payload]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=response_body
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/search/movie?api_key=test_api_key&query=Test%20Film&page=1&include_adult=false",
        json=response_body
    )

    service = TMDBService()
    discovered = await fetch_films(service)
    found = await find_films(service, FILM_QUERY)

    # Both tools expose the same top-level envelope
    assert discovered.keys() == found.keys()

    # Both tools describe an individual title with the same fields and values
    assert discovered["results"][0].keys() == found["results"][0].keys()
    assert discovered["results"][0] == found["results"][0]
