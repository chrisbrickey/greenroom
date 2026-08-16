"""Media retrieval tools for the greenroom MCP server.

Tool Flow:

- light registration layer
  These are FastMCP-annotated tool methods that delegate to methods that contain the domain logic.
  Testing the registration layer requires spinning up a server. See registration tests.

- orchestration layer
  These methods contain the orchestration logic extracted from the registration layer
  (e.g. browse_films, lookup_films) that is publicly available and testable without spinning up a server.

- util layer
  Helper modules that can be shared across tools to support consistency in the downstream logic
  (e.g. validation of inputs -> service calls -> formatting of response).
"""

from fastmcp import FastMCP

from greenroom.services.tmdb.service import TMDBService
from greenroom.tools.media.discover_tools import (
    browse_films,
    browse_television,
    register_discover_tools,
)
from greenroom.tools.media.search_tools import (
    lookup_films,
    lookup_television,
    register_search_tools,
)


def register_media_tools(mcp: FastMCP) -> None:
    """Register all media tools with the MCP server."""

    # The single place the provider is chosen. Registrars receive the instance
    # so that swapping providers is one edit rather than one per registrar.
    service = TMDBService()

    register_discover_tools(mcp, service)
    register_search_tools(mcp, service)


__all__ = [
    "register_media_tools",
    "browse_films",
    "browse_television",
    "lookup_films",
    "lookup_television",
]
