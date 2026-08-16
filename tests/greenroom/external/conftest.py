"""Shared fixtures and helpers for the external test tier.

Tests in this package make real network calls to third-party providers to confirm contracts.

These tests are resource-intensive so they are deselected from the default run.
Run with: `uv run pytest -m external`

Conventions for this external test tier:
1. Use low-level http clients (make the network call directly) to assert on a
   provider's own response envelope.
2. Assert through production code when the test is about behavior the tools
   promise to callers (e.g., filtering, translation, pagination). We want to run
   those checks through the same mapping layer that production uses so that drift
   in either the provider payload or the mapping is caught by the external test.
   Choose the layer that matches what the test covers:
   a) <provider>Service, when the test covers a single provider call
   b) the tools' orchestration methods (e.g. browse_films), when the test follows a
      journey across several tools, since that composition is what an agent drives
      and no lower layer exercises it.
3. Never hardcode catalog data that the provider can change. Read the seed value from
   the provider instead, through the same layer the test asserts on so that the seed
   and the assertion travel one path.
4. External tests should validate PROVIDER_PAGE_SIZE for each provider. Other
   external tests should make requests using that variable as the number of results
   to be returned so that every test inspects a full provider page. External tests
   should not use an internal service's default like DISCOVER_MAX_RESULTS.
5. As of 2026, TMDB ignores unrecognized parameters (returns 200 code).
   So asserting on a successful call does not test parameters well.
   Instead, external tests on TMDB should inspect the returned payload.
"""

import os

import pytest
from dotenv import load_dotenv

from greenroom.models.media import MediaList
from greenroom.services.media_limits import PROVIDER_PAGE_SIZE
from greenroom.services.tmdb.service import TMDBService

# Production code loads .env in server.py, so this tier loads it for itself
load_dotenv()

API_KEY_VARIABLE = "TMDB_API_KEY"

# MAX_BOUNDARY_OVERLAP helps pagination tests to assert that the next page advances through the catalog
# instead of asserting that consecutive pages are unique. Why? Because provider pagination windows
# are not perfectly consistent. For example, I observed with TMDB that a returned title sitting on the
# boundary between two pages can be served on both of them. It's a property of the provider that we accommodate.
#
# MAX_BOUNDARY_OVERLAP is set by what would actually break the test, not by how much TMDB drifts.
# If pagination broke on the TMDB server and page two repeated page one, then none of page two's titles would be new.
# Allowing a quarter of the page to repeat captures a complete pagination failure (all repeats).
# Allowing a lesser portion of overlap could raise false alarms on days when the catalog shuffles more than usual.
MAX_BOUNDARY_OVERLAP = PROVIDER_PAGE_SIZE // 4


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
