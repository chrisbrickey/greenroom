"""Shared constants and helpers for TMDBService tests."""

from dataclasses import dataclass
from typing import Any

from greenroom.services.tmdb.client import TMDBClient

TMDB_BASE_URL = TMDBClient.BASE_URL
TEST_API_KEY = "test_api_key"


@dataclass(frozen=True)
class SampleMedia:
    """The values a sample entry carries unchanged from provider payload to Media.

    This should only include fields the mapper copies verbatim so that a test value
    can be defined in one place and referenced both in the mock and the expectation.

    Values that require transformation are deliberately absent. For example, id is
    coerced to a string, date is parsed from a string, and media_type is stamped from
    the call rather than read from the payload. Those are written literally at each usage
    site in a test because the difference between the two forms is what the tests assert.
    """
    title: str
    description: str
    rating: float
    genre_ids: list[int]

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
