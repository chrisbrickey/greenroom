"""Tests for TMDBService protocol conformance and provider metadata."""

from greenroom.services.tmdb.service import TMDBService
from greenroom.services.protocols import MediaService


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
