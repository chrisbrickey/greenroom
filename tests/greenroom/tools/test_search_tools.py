"""Tests for the search-flow helpers (find_films, find_television) in discovery/search_tools.py."""

import pytest

from greenroom.tools.discovery import find_films, find_television
from greenroom.models.media import MediaList
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION

# Generic queries for the search helper tests
FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"
UNMATCHED_FILM_QUERY = "No Such Film"
UNMATCHED_TELEVISION_QUERY = "No Such Show"

# A single call fetches one provider page, so that page size is the most
# max_results can ever deliver
MAX_RESULTS_CEILING = 20
ABOVE_MAX_RESULTS = MAX_RESULTS_CEILING + 1
MAX_RESULTS_RANGE_MESSAGE = f"max_results must be between 1 and {MAX_RESULTS_CEILING}"


class TestFindFilms:
    """Tests for find_films helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, mock_media_service, sample_film_media_list):
        """Test find_films returns correctly formatted results."""
        mock_media_service.search_media.return_value = sample_film_media_list

        result = await find_films(mock_media_service, FILM_QUERY)

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
        """Test find_films uses MEDIA_TYPE_FILM and passes default parameters."""
        mock_media_service.search_media.return_value = sample_film_media_list

        await find_films(mock_media_service, FILM_QUERY)

        mock_media_service.search_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            query=FILM_QUERY,
            year=None,
            display_language=None,
            page=1,
            max_results=5
        )

    @pytest.mark.asyncio
    async def test_uses_film_media_type_with_custom_parameters(self, mock_media_service, sample_film_media_list):
        """Test find_films uses MEDIA_TYPE_FILM and passes custom parameters."""
        mock_media_service.search_media.return_value = sample_film_media_list

        await find_films(
            mock_media_service,
            FILM_QUERY,
            year=2003,
            display_language="es",
            page=3,
            max_results=15
        )

        mock_media_service.search_media.assert_called_once_with(
            media_type=MEDIA_TYPE_FILM,
            query=FILM_QUERY,
            year=2003,
            display_language="es",
            page=3,
            max_results=15
        )

    @pytest.mark.asyncio
    async def test_validates_query(self, mock_media_service, sample_film_media_list):
        """Test find_films requires a non-empty query."""
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            await find_films(mock_media_service, "")
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            await find_films(mock_media_service, "   ")

        # A real title should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY)

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_film_media_list):
        """Test find_films validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await find_films(mock_media_service, FILM_QUERY, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_film_media_list):
        """Test find_films validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await find_films(mock_media_service, FILM_QUERY, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await find_films(mock_media_service, FILM_QUERY, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_film_media_list):
        """Test find_films validates max_results parameter."""
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, max_results=0)
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, max_results=ABOVE_MAX_RESULTS)

        # Boundaries: 1 and the ceiling should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, max_results=1)
        await find_films(mock_media_service, FILM_QUERY, max_results=MAX_RESULTS_CEILING)

    @pytest.mark.asyncio
    async def test_validates_display_language(self, mock_media_service, sample_film_media_list):
        """Test find_films validates display_language parameter."""
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_films(mock_media_service, FILM_QUERY, display_language="eng")
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_films(mock_media_service, FILM_QUERY, display_language="e")
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_films(mock_media_service, FILM_QUERY, display_language="12")

        # Valid codes should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, display_language="en")
        await find_films(mock_media_service, FILM_QUERY, display_language="fr")

    @pytest.mark.asyncio
    async def test_empty_film_results(self, mock_media_service):
        """Test handling of empty results from service."""
        empty_list = MediaList(results=[], total_results=0, page=1, total_pages=0)
        mock_media_service.search_media.return_value = empty_list

        result = await find_films(mock_media_service, UNMATCHED_FILM_QUERY)

        assert result["results"] == []
        assert result["total_results"] == 0
        assert result["total_pages"] == 0


class TestFindTelevision:
    """Tests for find_television helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, mock_media_service, sample_tv_media_list):
        """Test find_television returns correctly formatted results."""
        mock_media_service.search_media.return_value = sample_tv_media_list

        result = await find_television(mock_media_service, TELEVISION_QUERY)

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
        """Test find_television uses MEDIA_TYPE_TELEVISION and passes default parameters."""
        mock_media_service.search_media.return_value = sample_tv_media_list

        await find_television(mock_media_service, TELEVISION_QUERY)

        mock_media_service.search_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            query=TELEVISION_QUERY,
            year=None,
            display_language=None,
            page=1,
            max_results=5
        )

    @pytest.mark.asyncio
    async def test_uses_television_media_type_with_custom_parameters(self, mock_media_service, sample_tv_media_list):
        """Test find_television uses MEDIA_TYPE_TELEVISION and passes custom parameters."""
        mock_media_service.search_media.return_value = sample_tv_media_list

        await find_television(
            mock_media_service,
            TELEVISION_QUERY,
            year=2022,
            display_language="fr",
            page=2,
            max_results=10
        )

        mock_media_service.search_media.assert_called_once_with(
            media_type=MEDIA_TYPE_TELEVISION,
            query=TELEVISION_QUERY,
            year=2022,
            display_language="fr",
            page=2,
            max_results=10
        )

    @pytest.mark.asyncio
    async def test_validates_query(self, mock_media_service, sample_tv_media_list):
        """Test find_television requires a non-empty query."""
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            await find_television(mock_media_service, "")
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            await find_television(mock_media_service, "   ")

        # A real title should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY)

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates year parameter."""
        with pytest.raises(ValueError, match="year must be 1900 or later"):
            await find_television(mock_media_service, TELEVISION_QUERY, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates page parameter."""
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await find_television(mock_media_service, TELEVISION_QUERY, page=0)
        with pytest.raises(ValueError, match="page must be 1 or greater"):
            await find_television(mock_media_service, TELEVISION_QUERY, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates max_results parameter."""
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, max_results=0)
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, max_results=ABOVE_MAX_RESULTS)

        # Boundaries: 1 and the ceiling should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, max_results=1)
        await find_television(mock_media_service, TELEVISION_QUERY, max_results=MAX_RESULTS_CEILING)

    @pytest.mark.asyncio
    async def test_validates_display_language(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates display_language parameter."""
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_television(mock_media_service, TELEVISION_QUERY, display_language="eng")
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_television(mock_media_service, TELEVISION_QUERY, display_language="e")
        with pytest.raises(ValueError, match="display_language must be a 2-character ISO 639-1 code"):
            await find_television(mock_media_service, TELEVISION_QUERY, display_language="12")

        # Valid codes should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, display_language="en")
        await find_television(mock_media_service, TELEVISION_QUERY, display_language="fr")

    @pytest.mark.asyncio
    async def test_empty_television_results(self, mock_media_service):
        """Test handling of empty results from service."""
        empty_list = MediaList(results=[], total_results=0, page=1, total_pages=0)
        mock_media_service.search_media.return_value = empty_list

        result = await find_television(mock_media_service, UNMATCHED_TELEVISION_QUERY)

        assert result["results"] == []
        assert result["total_results"] == 0
        assert result["total_pages"] == 0
