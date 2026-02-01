"""MCP tools for the greenroom server."""

from fastmcp import FastMCP

from greenroom.tools.genre_tools import register_genre_tools
from greenroom.tools.agent_tools import register_agent_tools
from greenroom.tools.discovery_tools import register_discovery_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tools with the MCP server."""
    register_genre_tools(mcp)
    register_agent_tools(mcp)
    register_discovery_tools(mcp)


__all__ = ["register_all_tools"]
