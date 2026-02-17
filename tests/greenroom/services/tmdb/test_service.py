"""Tests for TMDBService."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.exceptions import APIConnectionError, APIResponseError
from greenroom.services.tmdb.service import TMDBService
from greenroom.services.tmdb.config import TMDB_FILM_CONFIG
from greenroom.services.protocols import MediaService
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION


# =============================================================================
# Protocol conformance tests
# =============================================================================


def test_tmdb_service_satisfies_media_service_protocol(monkeypatch):
    """Test that TMDBService structurally satisfies the MediaService protocol."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()
    assert isinstance(service, MediaService)


def test_get_provider_name_returns_correct_string(monkeypatch):
    """Test get_provider_name returns 'TMDB'."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    assert service.get_provider_name() == "TMDB"


# =============================================================================
# get_media() tests
# =============================================================================


def test_get_media_returns_media_list_for_films(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media returns properly formatted MediaList for films."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {
                "id": 550,
                "title": "Fight Club",
                "release_date": "1999-10-15",
                "vote_average": 8.4,
                "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression.",
                "genre_ids": [18, 53],
                "poster_path": "/path.jpg"
            },
            {
                "id": 680,
                "title": "Pulp Fiction",
                "release_date": "1994-09-10",
                "vote_average": 8.5,
                "overview": "A burger-loving hit man, his philosophical partner, and a drug-addled gangster's moll.",
                "genre_ids": [80, 18],
                "popularity": 65.3
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres=18&primary_release_year=1999",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_FILM, genre_id=18, year=1999, page=1)

    assert result.page == 1
    assert result.total_results == 100
    assert result.total_pages == 5
    assert len(result.results) == 2
    assert result.results[0].title == "Fight Club"
    assert result.results[0].rating == 8.4
    assert result.results[0].genre_ids == [18, 53]
    assert result.results[0].media_type == MEDIA_TYPE_FILM
    assert result.results[1].title == "Pulp Fiction"


def test_get_media_returns_media_list_for_television(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media returns properly formatted MediaList for television shows."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 50,
        "total_pages": 3,
        "results": [
            {
                "id": 1399,
                "name": "Game of Thrones",
                "first_air_date": "2011-04-17",
                "vote_average": 8.4,
                "overview": "Seven noble families fight for control of the mythical land of Westeros.",
                "genre_ids": [10765, 18, 10759],
            },
            {
                "id": 1396,
                "name": "Breaking Bad",
                "first_air_date": "2008-01-20",
                "vote_average": 8.9,
                "overview": "A high school chemistry teacher turned meth manufacturer.",
                "genre_ids": [18, 80],
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres=18&first_air_date_year=2011",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_TELEVISION, genre_id=18, year=2011, page=1)

    assert result.page == 1
    assert result.total_results == 50
    assert result.total_pages == 3
    assert len(result.results) == 2
    assert result.results[0].title == "Game of Thrones"
    assert result.results[0].rating == 8.4
    assert result.results[0].genre_ids == [10765, 18, 10759]
    assert result.results[0].media_type == MEDIA_TYPE_TELEVISION
    assert result.results[0].date.isoformat() == "2011-04-17"
    assert result.results[1].title == "Breaking Bad"


def test_get_media_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that media with missing optional fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 5,
        "total_pages": 1,
        "results": [
            {"id": 1, "title": "Complete Film", "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Full details", "genre_ids": [28]},
            {"id": 2, "title": "Missing Date"},  # No release_date
            {"id": 3, "vote_average": 6.0},  # No title
            {"id": 4},  # Only ID
            {"id": 5, "title": "Invalid Date Film", "release_date": "not-a-date"},  # Invalid date format
            {"title": "No ID"},  # Missing ID - should be filtered out
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_FILM)

    # Should return 5 media items (all with IDs), not 6
    assert len(result.results) == 5

    # Check first item has all data
    assert result.results[0].title == "Complete Film"
    assert result.results[0].date.isoformat() == "2024-01-01"
    assert result.results[0].rating == 7.5
    assert result.results[0].description == "Full details"
    assert result.results[0].genre_ids == [28]

    # Check that missing fields are None or empty
    assert result.results[1].title == "Missing Date"
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


def test_get_media_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_media handles empty results gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_FILM)

    assert result.results == []
    assert result.total_results == 0
    assert result.page == 1
    assert result.total_pages == 0


def test_get_media_respects_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test that max_results parameter limits returned media."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock response with 20 films
    mock_results = [{"id": i, "title": f"Film {i}"} for i in range(20)]
    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": mock_results
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_FILM, max_results=5)

    assert len(result.results) == 5
    assert result.results[0].id == "0"
    assert result.results[4].id == "4"


def test_get_media_uses_default_parameters(monkeypatch, httpx_mock: HTTPXMock):
    """Test that get_media applies correct default parameters."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    service = TMDBService()
    service.get_media(media_type=MEDIA_TYPE_FILM)

    # Verify the mock was called with correct default URL
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert "sort_by=popularity.desc" in str(request.url)
    assert "page=1" in str(request.url)
    assert "include_adult=false" in str(request.url)


def test_get_media_filters_by_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test language parameter filters media correctly."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {"id": 123, "title": "Spanish Film", "original_language": "es"}
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_original_language=es",
        json=mock_response
    )

    service = TMDBService()
    result = service.get_media(media_type=MEDIA_TYPE_FILM, language="es")

    assert len(result.results) == 1
    assert result.results[0].title == "Spanish Film"

    # Verify the URL included the language parameter
    request = httpx_mock.get_requests()[0]
    assert "with_original_language=es" in str(request.url)


def test_get_media_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        service = TMDBService()

    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_get_media_raises_value_error_for_unsupported_media_type(monkeypatch):
    """Test that ValueError is raised for unsupported media types."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    with pytest.raises(ValueError) as exc_info:
        service.get_media(media_type="unsupported_type")

    assert "Unsupported media type" in str(exc_info.value)
    assert "unsupported_type" in str(exc_info.value)


def test_get_media_raises_api_response_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        status_code=401,
        text="Invalid API key"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_get_media_raises_api_response_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        content=b"Not valid JSON!"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "invalid JSON" in str(exc_info.value)


def test_get_media_raises_api_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false"
    )

    service = TMDBService()

    with pytest.raises(APIConnectionError) as exc_info:
        service.get_media(media_type=MEDIA_TYPE_FILM)

    assert "Failed to connect to TMDB API" in str(exc_info.value)


# =============================================================================
# get_genres() tests
# =============================================================================


def test_get_genres_combines_film_and_tv_genres(monkeypatch, httpx_mock: HTTPXMock):
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
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=film_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    service = TMDBService()
    result = service.get_genres()

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


def test_get_genres_drops_incomplete_genre_data(monkeypatch, httpx_mock: HTTPXMock):
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
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=film_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    service = TMDBService()
    result = service.get_genres()

    # Should only include valid genres
    assert len(result.genres) == 2
    genre_names = {g.name for g in result.genres}
    assert genre_names == {"Action", "Mystery"}


def test_get_genres_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test get_genres handles empty genre lists gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json={"genres": []}
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json={"genres": []}
    )

    service = TMDBService()
    result = service.get_genres()

    assert result.genres == []


def test_get_genres_raises_api_response_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        status_code=401,
        text="Invalid API key"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        service.get_genres()

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_get_genres_raises_api_response_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIResponseError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        content=b"Not valid JSON!"
    )

    service = TMDBService()

    with pytest.raises(APIResponseError) as exc_info:
        service.get_genres()

    assert "invalid JSON" in str(exc_info.value)


def test_get_genres_raises_api_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that APIConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key"
    )

    service = TMDBService()

    with pytest.raises(APIConnectionError) as exc_info:
        service.get_genres()

    assert "Failed to connect to TMDB API" in str(exc_info.value)
