"""Tests for the payload mapping in tmdb/media_mapper.py."""

from typing import Any

from greenroom.models.media_types import MEDIA_TYPE_FILM
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.config import TMDB_FILM_CONFIG
from greenroom.services.tmdb.media_mapper import to_media_list

# Fewer than a page holds, so the truncation is observable
REQUESTED_RESULTS = 3
REQUESTED_PAGE = 1


def build_page(result_count: int) -> dict[str, Any]:
    """Build a TMDB discover payload holding the given number of results.

    Args:
        result_count: How many results the payload should carry

    Returns:
        Dictionary shaped like a TMDB discover response, with ids counting up
        from zero so the returned order is verifiable
    """
    return {
        "page": REQUESTED_PAGE,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {"id": index, "title": f"Test Title {index}", "release_date": "2001-03-30"}
            for index in range(result_count)
        ],
    }


def test_keeps_only_the_requested_number_of_results() -> None:
    """A full page is truncated to the count the caller asked for."""

    media_list = to_media_list(
        build_page(PROVIDER_PAGE_SIZE),
        TMDB_FILM_CONFIG,
        MEDIA_TYPE_FILM,
        page=REQUESTED_PAGE,
        max_results=REQUESTED_RESULTS,
    )

    # Assert on ids (not just count) so that truncating from the wrong end would fail
    assert [media.id for media in media_list.results] == [
        str(index) for index in range(REQUESTED_RESULTS)
    ]


def test_returns_every_result_when_the_page_holds_fewer_than_requested() -> None:
    """A short page is returned whole rather than padded to the requested count."""

    short_page_size = REQUESTED_RESULTS - 1
    media_list = to_media_list(
        build_page(short_page_size),
        TMDB_FILM_CONFIG,
        MEDIA_TYPE_FILM,
        page=REQUESTED_PAGE,
        max_results=REQUESTED_RESULTS,
    )

    assert len(media_list.results) == short_page_size
