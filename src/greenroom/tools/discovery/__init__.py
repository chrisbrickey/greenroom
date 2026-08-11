"""Media retrieval tools for the greenroom MCP server."""

from fastmcp import FastMCP

from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.discovery.discovery_tools import (
    fetch_films,
    fetch_television,
    register_discovery_tools,
)


def register_all_discovery_tools(mcp: FastMCP) -> None:
    """Register all media discovery tools with the MCP server."""

    # The single place the provider is chosen. Registrars receive the instance
    # so that swapping providers is one edit rather than one per registrar.
    service = TMDBService()

    register_discovery_tools(mcp, service)


__all__ = [
    "register_all_discovery_tools",
    "fetch_films",
    "fetch_television",
]
