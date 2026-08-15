"""Shared fixtures for the tool-layer tests.

Provides one FastMCP server per registration function, so that tests can call
tools the way an agent does rather than reaching for the delegates directly.
"""

import pytest
from fastmcp import FastMCP

from greenroom.tools import register_all_tools
from greenroom.tools.agent_tools import register_agent_tools
from greenroom.tools.discovery import register_all_discovery_tools
from greenroom.tools.genre_tools import register_genre_tools

TEST_API_KEY = "test_api_key"


@pytest.fixture
def discovery_server(monkeypatch) -> FastMCP:
    """Create a FastMCP server with the discovery tools registered."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mcp = FastMCP("test-server")
    register_all_discovery_tools(mcp)
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
