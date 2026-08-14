"""Shared constants and helpers for TMDBService tests."""

from typing import Any

from greenroom.services.tmdb.client import TMDBClient

TMDB_BASE_URL = TMDBClient.BASE_URL
TEST_API_KEY = "test_api_key"

# Result count for truncation tests.
# Selected to be much smaller than any max-results default is ever expected to drift.
TRUNCATED_MAX_RESULTS = 2


def build_oversized_page(count: int) -> dict[str, Any]:
    """Build a provider response carrying more results than the caller will retain.

    Truncation tests need a page that is larger than the default they are checking.
    So the count is derived from that default rather than using a fixed number for results/page.
    The result may exceed what a real provider page can hold (PROVIDER_PAGE_SIZE), but
    that is deliberate because we need to prove that the caller truncates whatever it recieves.

    Args:
        count: Number of results to place on the page

    Returns:
        Dictionary shaped like a TMDB film response
    """
    return {
        "page": 1,
        "total_results": count,
        "total_pages": 1,
        "results": [
            {"id": index, "title": f"Test Film {index}", "release_date": "2020-01-01"}
            for index in range(1, count + 1)
        ]
    }
