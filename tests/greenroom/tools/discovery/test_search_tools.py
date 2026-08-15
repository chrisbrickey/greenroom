"""Tests the orchestration layer of MCP tools that search for single titles."""

import pytest

from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import MAX_RESULTS_MAX, MAX_RESULTS_MIN, SEARCH_MAX_RESULTS
from greenroom.tools.discovery import find_films, find_television

FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"
UNMATCHED_FILM_QUERY = "No Such Film"
UNMATCHED_TELEVISION_QUERY = "No Such Show"

# A single call fetches one provider page.
# So that page size is the most max_results can ever deliver.
ABOVE_MAX_RESULTS = MAX_RESULTS_MAX + 1
MAX_RESULTS_RANGE_MESSAGE = (
    f"max_results must be between {MAX_RESULTS_MIN} and {MAX_RESULTS_MAX}"
)

QUERY_MESSAGE = "query must be a non-empty string"
YEAR_MESSAGE = "year must be 1900 or later"
PAGE_MESSAGE = "page must be 1 or greater"
DISPLAY_LANGUAGE_MESSAGE = "display_language must be a 2-character ISO 639-1 code"

BLANK_QUERIES = ["", "   "]
MALFORMED_LANGUAGE_CODES = ["eng", "e", "12"]
VALID_LANGUAGE_CODES = ["en", "fr"]


class TestFindFilms:
    """Tests for find_films helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(
        self, mock_media_service, sample_film_media_list, expected_film_payload
    ):
        """Test find_films formats every field of the service payload."""
        mock_media_service.search_media.return_value = sample_film_media_list

        result = await find_films(mock_media_service, FILM_QUERY)

        assert result == expected_film_payload

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
            max_results=SEARCH_MAX_RESULTS
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
    @pytest.mark.parametrize("query", BLANK_QUERIES)
    async def test_rejects_blank_query(self, mock_media_service, query: str):
        """Test find_films requires a non-empty query."""
        with pytest.raises(ValueError, match=QUERY_MESSAGE):
            await find_films(mock_media_service, query)

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_film_media_list):
        """Test find_films validates year parameter."""
        with pytest.raises(ValueError, match=YEAR_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_film_media_list):
        """Test find_films validates page parameter."""
        with pytest.raises(ValueError, match=PAGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, page=0)
        with pytest.raises(ValueError, match=PAGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_film_media_list):
        """Test find_films validates max_results parameter."""
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, max_results=MAX_RESULTS_MIN - 1)
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, max_results=ABOVE_MAX_RESULTS)

        # Boundaries: both ends of the range should be accepted
        mock_media_service.search_media.return_value = sample_film_media_list
        await find_films(mock_media_service, FILM_QUERY, max_results=MAX_RESULTS_MIN)
        await find_films(mock_media_service, FILM_QUERY, max_results=MAX_RESULTS_MAX)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display_language", MALFORMED_LANGUAGE_CODES)
    async def test_rejects_malformed_display_language(self, mock_media_service, display_language: str):
        """Test find_films rejects a display_language that is not a 2-letter code."""
        with pytest.raises(ValueError, match=DISPLAY_LANGUAGE_MESSAGE):
            await find_films(mock_media_service, FILM_QUERY, display_language=display_language)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display_language", VALID_LANGUAGE_CODES)
    async def test_accepts_valid_display_language(
        self, mock_media_service, sample_film_media_list, display_language: str
    ):
        """Test find_films accepts a well-formed display_language."""
        mock_media_service.search_media.return_value = sample_film_media_list

        await find_films(mock_media_service, FILM_QUERY, display_language=display_language)

    @pytest.mark.asyncio
    async def test_empty_film_results(self, mock_media_service, empty_media_list, expected_empty_payload):
        """Test handling of empty results from service."""
        mock_media_service.search_media.return_value = empty_media_list

        result = await find_films(mock_media_service, UNMATCHED_FILM_QUERY)

        assert result == expected_empty_payload


class TestFindTelevision:
    """Tests for find_television helper function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_results(
        self, mock_media_service, sample_tv_media_list, expected_television_payload
    ):
        """Test find_television formats every field of the service payload."""
        mock_media_service.search_media.return_value = sample_tv_media_list

        result = await find_television(mock_media_service, TELEVISION_QUERY)

        assert result == expected_television_payload

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
            max_results=SEARCH_MAX_RESULTS
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
    @pytest.mark.parametrize("query", BLANK_QUERIES)
    async def test_rejects_blank_query(self, mock_media_service, query: str):
        """Test find_television requires a non-empty query."""
        with pytest.raises(ValueError, match=QUERY_MESSAGE):
            await find_television(mock_media_service, query)

    @pytest.mark.asyncio
    async def test_validates_year(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates year parameter."""
        with pytest.raises(ValueError, match=YEAR_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, year=1899)

        # Boundary: 1900 should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, year=1900)

    @pytest.mark.asyncio
    async def test_validates_page(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates page parameter."""
        with pytest.raises(ValueError, match=PAGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, page=0)
        with pytest.raises(ValueError, match=PAGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, page=-1)

        # Boundary: 1 should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, page=1)

    @pytest.mark.asyncio
    async def test_validates_max_results(self, mock_media_service, sample_tv_media_list):
        """Test find_television validates max_results parameter."""
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, max_results=MAX_RESULTS_MIN - 1)
        with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, max_results=ABOVE_MAX_RESULTS)

        # Boundaries: both ends of the range should be accepted
        mock_media_service.search_media.return_value = sample_tv_media_list
        await find_television(mock_media_service, TELEVISION_QUERY, max_results=MAX_RESULTS_MIN)
        await find_television(mock_media_service, TELEVISION_QUERY, max_results=MAX_RESULTS_MAX)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display_language", MALFORMED_LANGUAGE_CODES)
    async def test_rejects_malformed_display_language(self, mock_media_service, display_language: str):
        """Test find_television rejects a display_language that is not a 2-letter code."""
        with pytest.raises(ValueError, match=DISPLAY_LANGUAGE_MESSAGE):
            await find_television(mock_media_service, TELEVISION_QUERY, display_language=display_language)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display_language", VALID_LANGUAGE_CODES)
    async def test_accepts_valid_display_language(
        self, mock_media_service, sample_tv_media_list, display_language: str
    ):
        """Test find_television accepts a well-formed display_language."""
        mock_media_service.search_media.return_value = sample_tv_media_list

        await find_television(mock_media_service, TELEVISION_QUERY, display_language=display_language)

    @pytest.mark.asyncio
    async def test_empty_television_results(self, mock_media_service, empty_media_list, expected_empty_payload):
        """Test handling of empty results from service."""
        mock_media_service.search_media.return_value = empty_media_list

        result = await find_television(mock_media_service, UNMATCHED_TELEVISION_QUERY)

        assert result == expected_empty_payload
