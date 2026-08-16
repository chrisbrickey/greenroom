"""Shared fixtures and helpers for the tool-layer tests.

Tests in this directory build in-memory FastMCP servers and drive them with a client.
The servers, the sampling double, the provider URL patterns, and the payload builders
are extracted on this configuration file so that the test files describe the same world.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.client.sampling import SamplingMessage, SamplingParams
from pytest_httpx import HTTPXMock

from greenroom.tools import register_all_tools
from greenroom.tools.agent_tools import register_agent_tools
from greenroom.tools.genre_tools import register_genre_tools
from greenroom.tools.media import register_media_tools


PROVIDER_NAME = "TMDB"
TEST_API_KEY = "test_api_key"
FIRST_PAGE = 1


# =============================================================================
# Provider endpoints
# =============================================================================

FILM_SEARCH_PATH = "/3/search/movie"
TELEVISION_SEARCH_PATH = "/3/search/tv"
FILM_DISCOVER_PATH = "/3/discover/movie"
TELEVISION_DISCOVER_PATH = "/3/discover/tv"
FILM_GENRE_PATH = "/3/genre/movie/list"
TELEVISION_GENRE_PATH = "/3/genre/tv/list"


def _url_pattern(path: str) -> re.Pattern[str]:
    """Match any provider URL on the given path, whatever its query string."""
    return re.compile(rf".*{path}.*")


FILM_SEARCH_URL = _url_pattern(FILM_SEARCH_PATH)
TELEVISION_SEARCH_URL = _url_pattern(TELEVISION_SEARCH_PATH)
FILM_DISCOVER_URL = _url_pattern(FILM_DISCOVER_PATH)
TELEVISION_DISCOVER_URL = _url_pattern(TELEVISION_DISCOVER_PATH)
FILM_GENRE_LIST_URL = _url_pattern(FILM_GENRE_PATH)
TELEVISION_GENRE_LIST_URL = _url_pattern(TELEVISION_GENRE_PATH)


def requests_to(httpx_mock: HTTPXMock, path: str) -> list[httpx.Request]:
    """Requests the tools sent to one provider path, in the order they were sent.

    Args:
        httpx_mock: Fixture recording every request the tools made
        path: Provider URL path to filter on

    Returns:
        Matching requests, oldest first
    """
    return [request for request in httpx_mock.get_requests() if request.url.path == path]


# =============================================================================
# Servers, one per registration function
# =============================================================================


@pytest.fixture
def media_server(monkeypatch) -> FastMCP:
    """Create a FastMCP server with the media tools registered."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mcp = FastMCP("test-server")
    register_media_tools(mcp)
    return mcp


@pytest.fixture
def genre_server(monkeypatch) -> FastMCP:
    """Create a FastMCP server with the genre tools registered."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mcp = FastMCP("test-server")
    register_genre_tools(mcp)
    return mcp


@pytest.fixture
def agent_server() -> FastMCP:
    """Create a FastMCP server with the agent comparison tools registered."""
    mcp = FastMCP("test-server")
    register_agent_tools(mcp)
    return mcp


@pytest.fixture
def complete_server(monkeypatch) -> FastMCP:
    """Create a FastMCP server carrying every tool the project ships."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mcp = FastMCP("test-server")
    register_all_tools(mcp)
    return mcp


# =============================================================================
# Sampling double
# =============================================================================


@dataclass
class SamplingRecorder:
    """Client-side sampling handler that records requests and returns a canned reply.

    Attributes:
        reply: Text handed back to the tool for every sampling request
        requests: Sampling requests received, in the order the tool made them
    """
    reply: str
    requests: list[SamplingParams] = field(default_factory=list)

    async def __call__(
        self,
        messages: list[SamplingMessage],
        params: SamplingParams,
        context: object
    ) -> str:
        self.requests.append(params)
        return self.reply


def sampled_prompt(params: SamplingParams) -> str:
    """Return the text of the first message in a recorded sampling request."""
    return params.messages[0].content.text


# =============================================================================
# Provider genre payloads
# =============================================================================

# Deliberately absent from GENRE_MOOD_MAP in config.py, so every one of these takes
# the sampling path in categorize_genres. Tests that want the hardcoded path instead
# build their own catalog from the mood map.
FILM_ONLY_GENRE = "Sample Film Genre"
SHARED_GENRE = "Sample Shared Genre"
TELEVISION_ONLY_GENRE = "Sample Television Genre"

FILM_ONLY_GENRE_ID = 701
SHARED_GENRE_ID = 702
TELEVISION_ONLY_GENRE_ID = 703


def build_genre_response(entries: dict[str, int]) -> dict[str, Any]:
    """Build a provider genre payload from a name-to-id mapping.

    Args:
        entries: Genre name mapped to the id the provider publishes for it

    Returns:
        Dictionary shaped like a TMDB genre list response
    """
    return {"genres": [{"id": genre_id, "name": name} for name, genre_id in entries.items()]}


FILM_GENRE_RESPONSE = build_genre_response({
    FILM_ONLY_GENRE: FILM_ONLY_GENRE_ID,
    SHARED_GENRE: SHARED_GENRE_ID,
})

TELEVISION_GENRE_RESPONSE = build_genre_response({
    SHARED_GENRE: SHARED_GENRE_ID,
    TELEVISION_ONLY_GENRE: TELEVISION_ONLY_GENRE_ID,
})

EXPECTED_GENRE_PROPERTIES: dict[str, dict[str, Any]] = {
    FILM_ONLY_GENRE: {"id": FILM_ONLY_GENRE_ID, "has_films": True, "has_tv_shows": False},
    SHARED_GENRE: {"id": SHARED_GENRE_ID, "has_films": True, "has_tv_shows": True},
    TELEVISION_ONLY_GENRE: {"id": TELEVISION_ONLY_GENRE_ID, "has_films": False, "has_tv_shows": True},
}


@pytest.fixture
def genre_endpoints(httpx_mock) -> None:
    """Answer both provider genre endpoints with distinguishable payloads.

    Marked reusable because a journey can reach the genre catalog more than once,
    for instance when it categorizes genres and then resolves a name back to an id.
    """
    httpx_mock.add_response(url=FILM_GENRE_LIST_URL, json=FILM_GENRE_RESPONSE, is_reusable=True)
    httpx_mock.add_response(url=TELEVISION_GENRE_LIST_URL, json=TELEVISION_GENRE_RESPONSE, is_reusable=True)


# =============================================================================
# Provider media payloads
# =============================================================================

# TMDB response field names, which differ by media type
FILM_RESPONSE_FIELDS = ("title", "release_date")
TELEVISION_RESPONSE_FIELDS = ("name", "first_air_date")

FIRST_MEDIA_ID = 801
SAMPLE_TITLE_PREFIX = "sample-title"
SAMPLE_MEDIA_DATE = "2001-03-30"
SAMPLE_RATING = 7.5

EMPTY_MEDIA_RESPONSE: dict[str, Any] = {
    "page": FIRST_PAGE,
    "total_results": 0,
    "total_pages": 0,
    "results": [],
}


def build_media_response(
    title_field: str,
    date_field: str,
    genre_ids: list[int],
    count: int = 1,
    page: int = FIRST_PAGE
) -> dict[str, Any]:
    """Build a provider media payload whose every item carries the given genres.

    The discover and search endpoints return the same shape, so both flows are
    served from here. Each item gets a distinct id so truncation is observable.

    Args:
        title_field: Provider title field name ("title" or "name")
        date_field: Provider date field name ("release_date" or "first_air_date")
        genre_ids: Genre ids stamped on every item
        count: Number of items in the page
        page: Page number the payload reports

    Returns:
        Dictionary shaped like a TMDB discover or search response
    """
    return {
        "page": page,
        "total_results": count,
        "total_pages": 1,
        "results": [
            {
                "id": FIRST_MEDIA_ID + offset,
                title_field: f"{SAMPLE_TITLE_PREFIX}-{offset}",
                date_field: SAMPLE_MEDIA_DATE,
                "vote_average": SAMPLE_RATING,
                "genre_ids": list(genre_ids),
            }
            for offset in range(count)
        ]
    }
