"""Tests for TMDBService."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.services.tmdb.service import TMDBService
from greenroom.services.tmdb.config import TMDB_FILM_CONFIG
from greenroom.models.media_types import MEDIA_TYPE_FILM


def test_discover_returns_media_list_for_films(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover returns properly formatted MediaList for films."""
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
    result = service.discover(media_type=MEDIA_TYPE_FILM, genre_id=18, year=1999, page=1)

    assert result.page == 1
    assert result.total_results == 100
    assert result.total_pages == 5
    assert len(result.results) == 2
    assert result.results[0].title == "Fight Club"
    assert result.results[0].rating == 8.4
    assert result.results[0].genre_ids == [18, 53]
    assert result.results[0].media_type == MEDIA_TYPE_FILM
    assert result.results[1].title == "Pulp Fiction"


def test_discover_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that media with missing optional fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 4,
        "total_pages": 1,
        "results": [
            {"id": 1, "title": "Complete Film", "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Full details", "genre_ids": [28]},
            {"id": 2, "title": "Missing Date"},  # No release_date
            {"id": 3, "vote_average": 6.0},  # No title
            {"id": 4},  # Only ID
            {"title": "No ID"},  # Missing ID - should be filtered out
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    service = TMDBService()
    result = service.discover(media_type=MEDIA_TYPE_FILM)

    # Should return 4 media items (all with IDs), not 5
    assert len(result.results) == 4

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


def test_discover_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover handles empty results gracefully."""
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
    result = service.discover(media_type=MEDIA_TYPE_FILM)

    assert result.results == []
    assert result.total_results == 0
    assert result.page == 1
    assert result.total_pages == 0


def test_discover_respects_max_results(monkeypatch, httpx_mock: HTTPXMock):
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
    result = service.discover(media_type=MEDIA_TYPE_FILM, max_results=5)

    assert len(result.results) == 5
    assert result.results[0].id == "0"
    assert result.results[4].id == "4"


def test_discover_uses_default_parameters(monkeypatch, httpx_mock: HTTPXMock):
    """Test that discover applies correct default parameters."""
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
    service.discover(media_type=MEDIA_TYPE_FILM)

    # Verify the mock was called with correct default URL
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert "sort_by=popularity.desc" in str(request.url)
    assert "page=1" in str(request.url)
    assert "include_adult=false" in str(request.url)


def test_discover_filters_by_language(monkeypatch, httpx_mock: HTTPXMock):
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
    result = service.discover(media_type=MEDIA_TYPE_FILM, language="es")

    assert len(result.results) == 1
    assert result.results[0].title == "Spanish Film"

    # Verify the URL included the language parameter
    request = httpx_mock.get_requests()[0]
    assert "with_original_language=es" in str(request.url)


def test_discover_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        service = TMDBService()

    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_discover_raises_runtime_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        status_code=401,
        text="Invalid API key"
    )

    service = TMDBService()

    with pytest.raises(RuntimeError) as exc_info:
        service.discover(media_type=MEDIA_TYPE_FILM)

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_discover_raises_runtime_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        content=b"Not valid JSON!"
    )

    service = TMDBService()

    with pytest.raises(RuntimeError) as exc_info:
        service.discover(media_type=MEDIA_TYPE_FILM)

    assert "invalid JSON" in str(exc_info.value)


def test_discover_raises_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that ConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false"
    )

    service = TMDBService()

    with pytest.raises(ConnectionError) as exc_info:
        service.discover(media_type=MEDIA_TYPE_FILM)

    assert "Failed to connect to TMDB API" in str(exc_info.value)


def test_build_params_with_all_options(monkeypatch):
    """Test that _build_params creates correct parameter dict."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    params = service._build_params(
        config=TMDB_FILM_CONFIG,
        genre_id=28,
        year=2024,
        language="en",
        sort_by="vote_average.desc",
        page=2
    )

    assert params["with_genres"] == 28
    assert params["primary_release_year"] == 2024
    assert params["with_original_language"] == "en"
    assert params["sort_by"] == "vote_average.desc"
    assert params["page"] == 2
    assert params["include_adult"] is False
    assert params["include_video"] is False


def test_parse_response_filters_invalid_items(monkeypatch):
    """Test that _parse_response validates and filters media data."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    raw_results = [
        {"id": 1, "title": "Valid Film"},
        {"id": 2},  # Valid - only id required
        {"title": "No ID"},  # Invalid - missing id
        {},  # Invalid - missing id
        {"id": 3, "vote_average": 8.5, "genre_ids": [28, 12]},  # Valid
    ]

    result = service._parse_response(raw_results, TMDB_FILM_CONFIG)

    assert len(result) == 3
    assert result[0].id == 1
    assert result[0].title == "Valid Film"
    assert result[1].id == 2
    assert result[1].title is None
    assert result[2].id == 3
    assert result[2].vote_average == 8.5


def test_to_standard_media_transforms_correctly(monkeypatch):
    """Test that _to_standard_media creates correct Media objects."""
    from greenroom.services.tmdb.models import TMDBFilm

    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    service = TMDBService()

    tmdb_film = TMDBFilm(
        id=1,
        title="Test Film",
        release_date="2024-01-15",
        vote_average=8.0,
        overview="A test film",
        genre_ids=[28, 12]
    )

    result = service._to_standard_media(tmdb_film, TMDB_FILM_CONFIG, MEDIA_TYPE_FILM)

    assert result.id == "1"
    assert result.media_type == MEDIA_TYPE_FILM
    assert result.title == "Test Film"
    assert result.date.isoformat() == "2024-01-15"
    assert result.rating == 8.0
    assert result.description == "A test film"
    assert result.genre_ids == [28, 12]
