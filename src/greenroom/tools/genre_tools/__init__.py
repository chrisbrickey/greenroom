"""Genre-related tools for the greenroom MCP server."""

from fastmcp import FastMCP

from greenroom.tools.genre_tools.fetching import register_genre_fetching_tools
from greenroom.tools.genre_tools.operations import register_genre_operations_tools


def register_genre_tools(mcp: FastMCP) -> None:
    """Register all genre-related tools with the MCP server."""
    register_genre_fetching_tools(mcp)
    register_genre_operations_tools(mcp)


__all__ = ["register_genre_tools"]
