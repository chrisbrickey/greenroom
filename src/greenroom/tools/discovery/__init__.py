"""Media discovery and search tools for the greenroom MCP server.

The MCP surface is split by flow: discover_tools browses by filter criteria and
search_tools looks up a specific title. Both share the parameter checks in
validation.py and the response shaping in formatting.py.
"""

from fastmcp import FastMCP

from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.discovery.discover_tools import (
    fetch_films,
    fetch_television,
    register_discover_tools,
)
from greenroom.tools.discovery.search_tools import (
    find_films,
    find_television,
    register_search_tools,
)
from greenroom.tools.discovery.validation import VALID_SORT_OPTIONS


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register all media discovery and search tools with the MCP server."""

    # The single place the provider is chosen. Both flows share one instance so
    # that swapping providers is one edit rather than one per registrar.
    service = TMDBService()

    register_discover_tools(mcp, service)
    register_search_tools(mcp, service)


__all__ = [
    "register_discovery_tools",
    "fetch_films",
    "fetch_television",
    "find_films",
    "find_television",
    "VALID_SORT_OPTIONS",
]
