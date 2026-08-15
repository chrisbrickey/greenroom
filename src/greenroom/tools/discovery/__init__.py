"""Media retrieval tools for the greenroom MCP server.

Tool Flow:

- light registration layer
  These are FastMCP-annotated tool methods that delegate to methods that contain the domain logic.
  Testing the registration layer requires spinning up a server. See registration tests.

- orchestration layer
  These methods contain the orchestration logic extracted from the registration layer
  (e.g. fetch_films, fetch_television) that is publicly available and testable without spinning up a server.

- util layer
  Helper modules that can be shared across tools to support consistency in the downstream logic
  (e.g. validation of inputs -> service calls -> formatting of response).
"""

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
