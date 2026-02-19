"""Tests for discovery_tools.py tool layer."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, Mock

from greenroom.tools.discovery_tools import fetch_films, fetch_television
from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION

@pytest.fixture
def mock_media_service():
    """Create a mock media service."""
    service = Mock()
    service.get_provider_name.return_value = "TMDB"
    service.get_media = AsyncMock()
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

class TestFetchFilms:
    """Tests for fetch_films helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, mock_media_service, sample_film_media_list):
        """Test fetch_films returns correctly formatted results."""
        mock_media_service.get_media.return_value = sample_film_media_list

        result = await fetch_films(mock_media_service)

        assert result["page"] == 1
        assert result["total_results"] == 50
        assert result["total_pages"] == 3
        assert result["provider"] == "TMDB"
        assert len(result["results"]) == 2

        # Check first result with all fields populated
        assert result["results"][0]["id"] == "1"
        assert result["results"][0]["media_type"] == MEDIA_TYPE_FILM
        assert result["results"][0]["title"] == "Film 1"
        assert result["results"][0]["date"] == "2024-01-15"
        assert result["results"][0]["rating"] == 8.0
        assert result["results"][0]["description"] == "Description 1"
        assert result["results"][0]["genre_ids"] == [28]

        # Check second result with None values
        assert result["results"][1]["id"] == "2"
        assert result["results"][1]["date"] is None
        assert result["results"][1]["rating"] is None
        assert result["results"][1]["description"] is None
        assert result["results"][1]["genre_ids"] == []

    @pytest.mark.asyncio
    async def test_uses_film_media_type_and_default_parameters(self, mock_media_service, sample_film_media_list):
        """Test fetch_films uses MEDIA_TYPE_FILM and passes default parameters."""
        mock_media_service.get_media.return_value = sample_film_media_list

        await fetch_films(mock_media_service)

        mock_media_service.get_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            genre_id=None,
            year=None,
            language=None,
            sort_by=None,
            page=1,
            max_results=20
        )

    @pytest.mark.asyncio
    async def test_uses_film_media_type_with_custom_parameters(self, mock_media_service, sample_film_media_list):
        """Test fetch_films uses MEDIA_TYPE_FILM and passes custom parameters."""
        mock_media_service.get_media.return_value = sample_film_media_list

        await fetch_films(
            mock_media_service,
            genre_id=28,
            year=2024,
            language="es",
            sort_by="vote_average.desc",
            page=3,
            max_results=50
        )

        mock_media_service.get_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            genre_id=28,
            year=2024,
            language="es",
            sort_by="vote_average.desc",
            page=3,
            max_results=50
        )

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_film_media_list):
        """Test fetch_films validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await fetch_films(mock_media_service, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.get_media.return_value = sample_film_media_list
        await fetch_films(mock_media_service, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_film_media_list):
        """Test fetch_films validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await fetch_films(mock_media_service, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await fetch_films(mock_media_service, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.get_media.return_value = sample_film_media_list
        await fetch_films(mock_media_service, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_film_media_list):
        """Test fetch_films validates max_results parameter."""
        with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
            await fetch_films(mock_media_service, max_results=0)
        with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
            await fetch_films(mock_media_service, max_results=101)

        # Boundaries: 1 and 100 should be accepted
        mock_media_service.get_media.return_value = sample_film_media_list
        await fetch_films(mock_media_service, max_results=1)
        await fetch_films(mock_media_service, max_results=100)

    @pytest.mark.asyncio
    async def test_validates_language(self, mock_media_service, sample_film_media_list):
        """Test fetch_films validates language parameter."""
        with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
            await fetch_films(mock_media_service, language="eng")
        with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
            await fetch_films(mock_media_service, language="e")
        with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
            await fetch_films(mock_media_service, language="12")

        # Valid codes should be accepted
        mock_media_service.get_media.return_value = sample_film_media_list
        await fetch_films(mock_media_service, language="en")
        await fetch_films(mock_media_service, language="fr")

    @pytest.mark.asyncio
    async def test_validates_sort_by(self, mock_media_service, sample_film_media_list):
        """Test fetch_films validates sort_by parameter."""
        with pytest.raises(ValueError, match="sort_by must be one of"):
            await fetch_films(mock_media_service, sort_by="invalid_sort")

        # Valid options should be accepted
        mock_media_service.get_media.return_value = sample_film_media_list
        await fetch_films(mock_media_service, sort_by="popularity.desc")
        await fetch_films(mock_media_service, sort_by="date.asc")

    @pytest.mark.asyncio
    async def test_empty_film_results(self, mock_media_service):
        """Test handling of empty results from service."""
        empty_list = MediaList(results=[], total_results=0, page=1, total_pages=0)
        mock_media_service.get_media.return_value = empty_list

        result = await fetch_films(mock_media_service)

        assert result["results"] == []
        assert result["total_results"] == 0
        assert result["total_pages"] == 0

class TestFetchTelevision:
    """Tests for fetch_television helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television returns correctly formatted results."""
        mock_media_service.get_media.return_value = sample_tv_media_list

        result = await fetch_television(mock_media_service)

        assert result["page"] == 2
        assert result["total_results"] == 25
        assert result["total_pages"] == 5
        assert result["provider"] == "TMDB"
        assert len(result["results"]) == 1

        assert result["results"][0]["id"] == "101"
        assert result["results"][0]["media_type"] == MEDIA_TYPE_TELEVISION
        assert result["results"][0]["title"] == "TV Show 1"
        assert result["results"][0]["date"] == "2024-03-20"
        assert result["results"][0]["rating"] == 9.0
        assert result["results"][0]["description"] == "TV Description 1"
        assert result["results"][0]["genre_ids"] == [18, 10765]

    @pytest.mark.asyncio
    async def test_uses_television_media_type_and_default_parameters(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television uses MEDIA_TYPE_TELEVISION and passes default parameters."""
        mock_media_service.get_media.return_value = sample_tv_media_list

        await fetch_television(mock_media_service)

        mock_media_service.get_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            genre_id=None,
            year=None,
            language=None,
            sort_by=None,
            page=1,
            max_results=20
        )

    @pytest.mark.asyncio
    async def test_uses_television_media_type_with_custom_parameters(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television uses MEDIA_TYPE_TELEVISION and passes custom parameters."""
        mock_media_service.get_media.return_value = sample_tv_media_list

        await fetch_television(
            mock_media_service,
            genre_id=18,
            year=2023,
            language="fr",
            sort_by="date.asc",
            page=5,
            max_results=75
        )

        mock_media_service.get_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            genre_id=18,
            year=2023,
            language="fr",
            sort_by="date.asc",
            page=5,
            max_results=75
        )

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await fetch_television(mock_media_service, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.get_media.return_value = sample_tv_media_list
        await fetch_television(mock_media_service, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await fetch_television(mock_media_service, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await fetch_television(mock_media_service, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.get_media.return_value = sample_tv_media_list
        await fetch_television(mock_media_service, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television validates max_results parameter."""
        with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
            await fetch_television(mock_media_service, max_results=0)
        with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
            await fetch_television(mock_media_service, max_results=101)

        # Boundaries: 1 and 100 should be accepted
        mock_media_service.get_media.return_value = sample_tv_media_list
        await fetch_television(mock_media_service, max_results=1)
        await fetch_television(mock_media_service, max_results=100)

    @pytest.mark.asyncio
    async def test_validates_language(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television validates language parameter."""
        with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
            await fetch_television(mock_media_service, language="english")

        # Valid codes should be accepted
        mock_media_service.get_media.return_value = sample_tv_media_list
        await fetch_television(mock_media_service, language="en")

    @pytest.mark.asyncio
    async def test_validates_sort_by(self, mock_media_service, sample_tv_media_list):
        """Test fetch_television validates sort_by parameter."""
        with pytest.raises(ValueError, match="sort_by must be one of"):
            await fetch_television(mock_media_service, sort_by="name.asc")

        # Valid options should be accepted
        mock_media_service.get_media.return_value = sample_tv_media_list
        await fetch_television(mock_media_service, sort_by="popularity.desc")

    @pytest.mark.asyncio
    async def test_empty_television_results(self, mock_media_service):
        """Test handling of empty results from service."""
        empty_list = MediaList(results=[], total_results=0, page=1, total_pages=0)
        mock_media_service.get_media.return_value = empty_list

        result = await fetch_television(mock_media_service)

        assert result["results"] == []
        assert result["total_results"] == 0
        assert result["total_pages"] == 0
