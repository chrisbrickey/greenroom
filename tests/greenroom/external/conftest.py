"""Shared fixtures and helpers for the external test tier.

Tests in this package make real network calls to third-party providers to confirm contracts.

These tests are resource-intensive so they are deselected from the default run.
Run with: `uv run pytest -m external`

Conventions for this external test tier:
1. Use low-level http clients (make the network call directly) in two scenarios:
   a) to assert on a provider's own response envelope
   b) to read a fixture value from a provider rather than hardcoding catalog data that can change.
2. Assert through <provider>Service when the test is about behavior the tools
   promise to callers (e.g., filtering, translation, pagination). We want to run
   those checks through the same mapping layer that production uses so that drift
   in either the provider payload or the mapping is caught by the external test.
3. External tests should validate PROVIDER_PAGE_SIZE for each provider. Other
   external tests whould make requests using that variable as the number of results
   to be returned so that every test inspects a full provider page. External tests
   should not use an internal service's default like DISCOVER_MAX_RESULTS.
4. As of 2026, TMDB ignores unrecognized parameters (returns 200 code).
   So asserting on a successful call does not test parameters well.
   Instead, external tests on TMDB should inspect the returned payload.
"""

import os

import pytest
from dotenv import load_dotenv

from greenroom.models.media import MediaList
from greenroom.services.tmdb.service import TMDBService

# Production code loads .env in server.py, so this tier loads it for itself
load_dotenv()

API_KEY_VARIABLE = "TMDB_API_KEY"

# Pagination tests assert that the next page advances through the catalog
# instead of asserting that consecutive pages are unique. Why? Because
# provider pagination windows are not perfectly consistent.
# For example, I observed with TMDB that a returned title sitting on the
# boundary between two pages can be served on both of them.
# It's a property of the provider that we must accommodate.
MAX_BOUNDARY_OVERLAP = 2


@pytest.fixture
def tmdb_service() -> TMDBService:
    """Real TMDBService wired to the live provider.

    Skips rather than fails when no credential is configured,
    so a contributor without an API key still gets a clean run.
    """
    if not os.getenv(API_KEY_VARIABLE):
        pytest.skip(f"{API_KEY_VARIABLE} is not configured")

    return TMDBService()


def media_ids_in_returned_order(media_list: MediaList) -> list[str]:
    """Ids, in the order the provider returned them."""
    return [item.id for item in media_list.results]
