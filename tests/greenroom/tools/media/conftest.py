"""Shared fixtures for the media tool-layer tests."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.models.responses import MediaPageDict
from greenroom.services.protocols import MediaService

from ..conftest import PROVIDER_NAME

EXPECTED_FILM_PAYLOAD: MediaPageDict = {
    "results": [
        {
            "id": "1",
            "media_type": MEDIA_TYPE_FILM,
            "title": "Film 1",
            "date": "2024-01-15",
            "rating": 8.0,
            "description": "Description 1",
            "genre_ids": [28]
        },
        {
            "id": "2",
            "media_type": MEDIA_TYPE_FILM,
            "title": "Film 2",
            "date": None,
            "rating": None,
            "description": None,
            "genre_ids": []
        },
    ],
    "total_results": 50,
    "page": 1,
    "total_pages": 3,
    "provider": PROVIDER_NAME
}

EXPECTED_TELEVISION_PAYLOAD: MediaPageDict = {
    "results": [
        {
            "id": "101",
            "media_type": MEDIA_TYPE_TELEVISION,
            "title": "TV Show 1",
            "date": "2024-03-20",
            "rating": 9.0,
            "description": "TV Description 1",
            "genre_ids": [18, 10765]
        },
    ],
    "total_results": 25,
    "page": 2,
    "total_pages": 5,
    "provider": PROVIDER_NAME
}

EXPECTED_EMPTY_PAYLOAD: MediaPageDict = {
    "results": [],
    "total_results": 0,
    "page": 1,
    "total_pages": 0,
    "provider": PROVIDER_NAME
}


@pytest.fixture
def mock_media_service() -> Mock:
    """Create a mock media service."""
    service = Mock(spec=MediaService)
    service.get_provider_name.return_value = PROVIDER_NAME
    service.discover_media = AsyncMock()
    service.search_media = AsyncMock()
    return service


@pytest.fixture
def sample_film_media_list() -> MediaList:
    """Create sample film MediaList for testing.

    The second film leaves every optional field unset, which exercises the
    None and empty-list paths in formatting.
    """
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
def sample_tv_media_list() -> MediaList:
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


@pytest.fixture
def empty_media_list() -> MediaList:
    """Create an empty MediaList for testing the no-results path."""
    return MediaList(results=[], total_results=0, page=1, total_pages=0)


@pytest.fixture
def expected_film_payload() -> MediaPageDict:
    """The formatted payload that sample_film_media_list should produce."""
    return EXPECTED_FILM_PAYLOAD


@pytest.fixture
def expected_television_payload() -> MediaPageDict:
    """The formatted payload that sample_tv_media_list should produce."""
    return EXPECTED_TELEVISION_PAYLOAD


@pytest.fixture
def expected_empty_payload() -> MediaPageDict:
    """The formatted payload that empty_media_list should produce."""
    return EXPECTED_EMPTY_PAYLOAD
