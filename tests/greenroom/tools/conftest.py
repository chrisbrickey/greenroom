"""Shared fixtures for the discovery tool-layer tests."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION


@pytest.fixture
def mock_media_service():
    """Create a mock media service."""
    service = Mock()
    service.get_provider_name.return_value = "TMDB"
    service.get_media = AsyncMock()
    service.search_media = AsyncMock()
    return service


@pytest.fixture
def sample_film_media_list():
    """Create sample film MediaList for testing."""
    return MediaList(
        results=[
            Media(
                id="1",
                media_type=MEDIA_TYPE_FILM,
                title="Film 1",
                date=date(2024, 1, 15),
                rating=8.0,
                description="Description 1",
                genre_ids=[28]
            ),
            Media(
                id="2",
                media_type=MEDIA_TYPE_FILM,
                title="Film 2",
                date=None,
                rating=None,
                description=None,
                genre_ids=[]
            ),
        ],
        total_results=50,
        page=1,
        total_pages=3
    )


@pytest.fixture
def sample_tv_media_list():
    """Create sample television MediaList for testing."""
    return MediaList(
        results=[
            Media(
                id="101",
                media_type=MEDIA_TYPE_TELEVISION,
                title="TV Show 1",
                date=date(2024, 3, 20),
                rating=9.0,
                description="TV Description 1",
                genre_ids=[18, 10765]
            ),
        ],
        total_results=25,
        page=2,
        total_pages=5
    )
