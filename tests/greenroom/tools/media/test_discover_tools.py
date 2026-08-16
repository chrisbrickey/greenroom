"""Tests the orchestration layer of MCP tools that browse content with filtering criteria."""

import pytest

from greenroom.services.media_limits import DISCOVER_MAX_RESULTS
from greenroom.tools.media.discover_tools import browse_films, browse_television
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION


class TestFetchFilms:
    """Tests for browse_films orchestration function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(
        self, mock_media_service, sample_film_media_list, expected_film_payload
    ):
        """Test browse_films formats every field of the service payload."""
        mock_media_service.discover_media.return_value = sample_film_media_list

        result = await browse_films(mock_media_service)

        assert result == expected_film_payload

    @pytest.mark.asyncio
    async def test_uses_film_media_type_and_default_parameters(self, mock_media_service, sample_film_media_list):
        """Test browse_films uses MEDIA_TYPE_FILM and passes default parameters."""
        mock_media_service.discover_media.return_value = sample_film_media_list

        await browse_films(mock_media_service)

        mock_media_service.discover_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            genre_id=None,
            year=None,
            original_language=None,
            sort_by=None,
            page=1,
            max_results=DISCOVER_MAX_RESULTS
        )

    @pytest.mark.asyncio
    async def test_uses_film_media_type_with_custom_parameters(self, mock_media_service, sample_film_media_list):
        """Test browse_films uses MEDIA_TYPE_FILM and passes custom parameters."""
        mock_media_service.discover_media.return_value = sample_film_media_list

        await browse_films(
            mock_media_service,
            genre_id=28,
            year=2024,
            original_language="es",
            sort_by="vote_average.desc",
            page=3,
            max_results=15
        )

        mock_media_service.discover_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            genre_id=28,
            year=2024,
            original_language="es",
            sort_by="vote_average.desc",
            page=3,
            max_results=15
        )

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_film_media_list):
        """Test browse_films validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await browse_films(mock_media_service, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.discover_media.return_value = sample_film_media_list
        await browse_films(mock_media_service, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_film_media_list):
        """Test browse_films validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await browse_films(mock_media_service, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await browse_films(mock_media_service, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.discover_media.return_value = sample_film_media_list
        await browse_films(mock_media_service, page=1)

    @pytest.mark.asyncio
    async def test_validates_original_language(self, mock_media_service, sample_film_media_list):
        """Test browse_films validates original_language parameter."""
        with pytest.raises(ValueError, match="original_language must be a 2-character ISO 639-1 code"):
            await browse_films(mock_media_service, original_language="eng")
        with pytest.raises(ValueError, match="original_language must be a 2-character ISO 639-1 code"):
            await browse_films(mock_media_service, original_language="e")
        with pytest.raises(ValueError, match="original_language must be a 2-character ISO 639-1 code"):
            await browse_films(mock_media_service, original_language="12")

        # Valid codes should be accepted
        mock_media_service.discover_media.return_value = sample_film_media_list
        await browse_films(mock_media_service, original_language="en")
        await browse_films(mock_media_service, original_language="fr")

    @pytest.mark.asyncio
    async def test_validates_sort_by(self, mock_media_service, sample_film_media_list):
        """Test browse_films validates sort_by parameter."""
        with pytest.raises(ValueError, match="sort_by must be one of"):
            await browse_films(mock_media_service, sort_by="invalid_sort")

        # Valid options should be accepted
        mock_media_service.discover_media.return_value = sample_film_media_list
        await browse_films(mock_media_service, sort_by="popularity.desc")
        await browse_films(mock_media_service, sort_by="date.asc")

    @pytest.mark.asyncio
    async def test_empty_film_results(self, mock_media_service, empty_media_list, expected_empty_payload):
        """Test handling of empty results from service."""
        mock_media_service.discover_media.return_value = empty_media_list

        result = await browse_films(mock_media_service)

        assert result == expected_empty_payload


class TestFetchTelevision:
    """Tests for browse_television orchestration function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(
        self, mock_media_service, sample_tv_media_list, expected_television_payload
    ):
        """Test browse_television formats every field of the service payload."""
        mock_media_service.discover_media.return_value = sample_tv_media_list

        result = await browse_television(mock_media_service)

        assert result == expected_television_payload

    @pytest.mark.asyncio
    async def test_uses_television_media_type_and_default_parameters(self, mock_media_service, sample_tv_media_list):
        """Test browse_television uses MEDIA_TYPE_TELEVISION and passes default parameters."""
        mock_media_service.discover_media.return_value = sample_tv_media_list

        await browse_television(mock_media_service)

        mock_media_service.discover_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            genre_id=None,
            year=None,
            original_language=None,
            sort_by=None,
            page=1,
            max_results=DISCOVER_MAX_RESULTS
        )

    @pytest.mark.asyncio
    async def test_uses_television_media_type_with_custom_parameters(self, mock_media_service, sample_tv_media_list):
        """Test browse_television uses MEDIA_TYPE_TELEVISION and passes custom parameters."""
        mock_media_service.discover_media.return_value = sample_tv_media_list

        await browse_television(
            mock_media_service,
            genre_id=18,
            year=2023,
            original_language="fr",
            sort_by="date.asc",
            page=5,
            max_results=12
        )

        mock_media_service.discover_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            genre_id=18,
            year=2023,
            original_language="fr",
            sort_by="date.asc",
            page=5,
            max_results=12
        )

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_tv_media_list):
        """Test browse_television validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await browse_television(mock_media_service, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.discover_media.return_value = sample_tv_media_list
        await browse_television(mock_media_service, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_tv_media_list):
        """Test browse_television validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await browse_television(mock_media_service, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await browse_television(mock_media_service, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.discover_media.return_value = sample_tv_media_list
        await browse_television(mock_media_service, page=1)

    @pytest.mark.asyncio
    async def test_validates_original_language(self, mock_media_service, sample_tv_media_list):
        """Test browse_television validates original_language parameter."""
        with pytest.raises(ValueError, match="original_language must be a 2-character ISO 639-1 code"):
            await browse_television(mock_media_service, original_language="english")

        # Valid codes should be accepted
        mock_media_service.discover_media.return_value = sample_tv_media_list
        await browse_television(mock_media_service, original_language="en")

    @pytest.mark.asyncio
    async def test_validates_sort_by(self, mock_media_service, sample_tv_media_list):
        """Test browse_television validates sort_by parameter."""
        with pytest.raises(ValueError, match="sort_by must be one of"):
            await browse_television(mock_media_service, sort_by="name.asc")

        # Valid options should be accepted
        mock_media_service.discover_media.return_value = sample_tv_media_list
        await browse_television(mock_media_service, sort_by="popularity.desc")

    @pytest.mark.asyncio
    async def test_empty_television_results(self, mock_media_service, empty_media_list, expected_empty_payload):
        """Test handling of empty results from service."""
        mock_media_service.discover_media.return_value = empty_media_list

        result = await browse_television(mock_media_service)

        assert result == expected_empty_payload
