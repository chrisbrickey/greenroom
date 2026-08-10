"""Shared fixtures for the external test tier.

Tests in this package make real network calls to third-party providers
so they are deselected from the default run.

Run with: `uv run pytest -m external`
"""

import os

import pytest
from dotenv import load_dotenv

from greenroom.services.tmdb.service import TMDBService

# Production code loads .env in server.py, so this tier loads it for itself
load_dotenv()

API_KEY_VARIABLE = "TMDB_API_KEY"


@pytest.fixture
def tmdb_service() -> TMDBService:
    """Real TMDBService wired to the live provider.

    Skips rather than fails when no credential is configured, so a contributor
    without an API key still gets a clean run.
    """
    if not os.getenv(API_KEY_VARIABLE):
        pytest.skip(f"{API_KEY_VARIABLE} is not configured")

    return TMDBService()
