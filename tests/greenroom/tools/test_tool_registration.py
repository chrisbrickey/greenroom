"""Tests that discovery tools are registered with the MCP server and wired correctly.

These tests cover only the tool registration layer: method names of the actual FastMCP
tools, their input parameter schemas, and the arguments that each tool forwards to its helper.

The helper methods, which can be called directly in tests without spinning up an MCP server,
contain the actual logic for each tool and those methods are comprehensively tested elsewhere.
"""

import pytest
from dataclasses import dataclass, field
from typing import Any
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from greenroom.tools.discovery import register_discovery_tools
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import DISCOVER_MAX_RESULTS, SEARCH_MAX_RESULTS

TEST_API_KEY = "test_api_key"
PROVIDER_NAME = "TMDB"

# Generic queries
FILM_QUERY = "Test Film"
TELEVISION_QUERY = "Test Show"

# Distinct values so that a mix-up between two arguments changes the outgoing request
REQUESTED_GENRE_ID = 28
REQUESTED_YEAR = 2001
REQUESTED_LANGUAGE = "es"
REQUESTED_SORT_BY = "vote_average.desc"
REQUESTED_PAGE = 2
REQUESTED_MAX_RESULTS = 1

DISCOVERY_PARAMETERS = ["genre_id", "year", "language", "sort_by", "page", "max_results"]
SEARCH_PARAMETERS = ["query", "year", "display_language", "page", "max_results"]

# Parameters the search endpoints must never send, since only discovery supports them
DISCOVERY_ONLY_PARAMS = ("sort_by", "with_original_language")

# TMDB response field names, which differ by media type
FILM_RESPONSE_FIELDS = ("title", "release_date")
TELEVISION_RESPONSE_FIELDS = ("name", "first_air_date")


@dataclass(frozen=True)
class ToolCase:
    """A registered tool paired with the provider request it is expected to produce.

    Attributes:
        tool_name: Name the tool is registered under
        arguments: Arguments an agent supplies when calling the tool
        expected_parameters: Parameter names the tool advertises, in order
        expected_required: Parameter names the tool marks as required
        expected_path: Provider URL path the tool is expected to call
        expected_provider_params: Provider query params the arguments map onto
        expected_media_type: Media type the returned results carry
        response_fields: Provider title and date field names for this media type
        expected_max_results_default: max_results value this tool advertises
                                      when the caller supplies none
        forbidden_params: Provider query params this tool must never send
    """
    tool_name: str
    arguments: dict[str, Any]
    expected_parameters: list[str]
    expected_required: list[str]
    expected_path: str
    expected_provider_params: dict[str, str]
    expected_media_type: str
    response_fields: tuple[str, str]
    expected_max_results_default: int
    forbidden_params: tuple[str, ...] = field(default=())


DISCOVERY_ARGUMENTS: dict[str, Any] = {
    "genre_id": REQUESTED_GENRE_ID,
    "year": REQUESTED_YEAR,
    "language": REQUESTED_LANGUAGE,
    "sort_by": REQUESTED_SORT_BY,
    "page": REQUESTED_PAGE,
    "max_results": REQUESTED_MAX_RESULTS,
}

SHARED_DISCOVERY_PARAMS: dict[str, str] = {
    "with_genres": str(REQUESTED_GENRE_ID),
    "with_original_language": REQUESTED_LANGUAGE,
    "sort_by": REQUESTED_SORT_BY,
    "page": str(REQUESTED_PAGE),
}


def build_search_arguments(query: str) -> dict[str, Any]:
    """Build the arguments an agent supplies when calling a search tool.

    Args:
        query: Title text to search for

    Returns:
        Dictionary of tool arguments
    """
    return {
        "query": query,
        "year": REQUESTED_YEAR,
        "display_language": REQUESTED_LANGUAGE,
        "page": REQUESTED_PAGE,
        "max_results": REQUESTED_MAX_RESULTS,
    }


def build_search_params(query: str, year_param: str) -> dict[str, str]:
    """Build the provider query params a search tool is expected to send.

    Args:
        query: Title text expected to reach the provider
        year_param: Provider year parameter name for this media type

    Returns:
        Dictionary of expected provider query params
    """
    return {
        "query": query,
        year_param: str(REQUESTED_YEAR),
        "language": REQUESTED_LANGUAGE,
        "page": str(REQUESTED_PAGE),
    }


TOOL_CASES = [
    ToolCase(
        tool_name="discover_films",
        arguments=DISCOVERY_ARGUMENTS,
        expected_parameters=DISCOVERY_PARAMETERS,
        expected_required=[],
        expected_path="/3/discover/movie",
        expected_provider_params={**SHARED_DISCOVERY_PARAMS, "primary_release_year": str(REQUESTED_YEAR)},
        expected_media_type=MEDIA_TYPE_FILM,
        response_fields=FILM_RESPONSE_FIELDS,
        expected_max_results_default=DISCOVER_MAX_RESULTS,
    ),
    ToolCase(
        tool_name="discover_television",
        arguments=DISCOVERY_ARGUMENTS,
        expected_parameters=DISCOVERY_PARAMETERS,
        expected_required=[],
        expected_path="/3/discover/tv",
        expected_provider_params={**SHARED_DISCOVERY_PARAMS, "first_air_date_year": str(REQUESTED_YEAR)},
        expected_media_type=MEDIA_TYPE_TELEVISION,
        response_fields=TELEVISION_RESPONSE_FIELDS,
        expected_max_results_default=DISCOVER_MAX_RESULTS,
    ),
    ToolCase(
        tool_name="search_films",
        arguments=build_search_arguments(FILM_QUERY),
        expected_parameters=SEARCH_PARAMETERS,
        expected_required=["query"],
        expected_path="/3/search/movie",
        expected_provider_params=build_search_params(FILM_QUERY, "primary_release_year"),
        expected_media_type=MEDIA_TYPE_FILM,
        response_fields=FILM_RESPONSE_FIELDS,
        expected_max_results_default=SEARCH_MAX_RESULTS,
        forbidden_params=DISCOVERY_ONLY_PARAMS,
    ),
    ToolCase(
        tool_name="search_television",
        arguments=build_search_arguments(TELEVISION_QUERY),
        expected_parameters=SEARCH_PARAMETERS,
        expected_required=["query"],
        expected_path="/3/search/tv",
        expected_provider_params=build_search_params(TELEVISION_QUERY, "first_air_date_year"),
        expected_media_type=MEDIA_TYPE_TELEVISION,
        response_fields=TELEVISION_RESPONSE_FIELDS,
        expected_max_results_default=SEARCH_MAX_RESULTS,
        forbidden_params=DISCOVERY_ONLY_PARAMS,
    ),
]

SEARCH_TOOL_NAMES = [case.tool_name for case in TOOL_CASES if case.expected_required]


@pytest.fixture
def discovery_server(monkeypatch) -> FastMCP:
    """Create a FastMCP server with the discovery tools registered."""
    monkeypatch.setenv("TMDB_API_KEY", TEST_API_KEY)

    mcp = FastMCP("test-server")
    register_discovery_tools(mcp)
    return mcp


def build_two_result_response(title_field: str, date_field: str) -> dict[str, Any]:
    """Build a provider response with two results, so max_results truncation is observable.

    Args:
        title_field: Provider title field name ("title" or "name")
        date_field: Provider date field name ("release_date" or "first_air_date")

    Returns:
        Dictionary shaped like a TMDB discover or search response
    """
    return {
        "page": REQUESTED_PAGE,
        "total_results": 2,
        "total_pages": 1,
        "results": [
            {"id": 601, title_field: "Test Title One", date_field: "2001-03-30", "vote_average": 8.2, "genre_ids": [REQUESTED_GENRE_ID]},
            {"id": 602, title_field: "Test Title Two", date_field: "2001-05-15", "vote_average": 7.0, "genre_ids": [REQUESTED_GENRE_ID]},
        ]
    }


def case_id(case: ToolCase) -> str:
    """Name each parametrized case after the tool it exercises."""
    return case.tool_name


# =============================================================================
# Registration and exposed schema
# =============================================================================


@pytest.mark.asyncio
async def test_all_discovery_tools_are_registered(discovery_server):
    """Test that every discovery tool is exposed to agents."""
    tools = await discovery_server.get_tools()

    assert {case.tool_name for case in TOOL_CASES}.issubset(set(tools))


@pytest.mark.asyncio
@pytest.mark.parametrize("case", TOOL_CASES, ids=case_id)
async def test_tool_exposes_expected_parameters(discovery_server, case: ToolCase):
    """Test that each tool advertises its parameters and marks the right ones required."""
    tools = await discovery_server.get_tools()
    schema = tools[case.tool_name].parameters

    assert list(schema["properties"]) == case.expected_parameters
    assert schema.get("required", []) == case.expected_required


@pytest.mark.asyncio
@pytest.mark.parametrize("case", TOOL_CASES, ids=case_id)
async def test_tool_advertises_shared_max_results_default(discovery_server, case: ToolCase):
    """Test the default an agent sees matches the one definition of that policy.

    The tool signature is what reaches the published schema, so a signature that
    drifts from media_limits would quietly serve agents a different default than
    every other layer applies.
    """
    tools = await discovery_server.get_tools()
    schema = tools[case.tool_name].parameters

    assert schema["properties"]["max_results"]["default"] == case.expected_max_results_default


# =============================================================================
# Argument routing through the registered tools
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", TOOL_CASES, ids=case_id)
async def test_tool_forwards_arguments_to_provider(discovery_server, httpx_mock, case: ToolCase):
    """Test each tool routes its arguments onto the matching provider parameters."""
    httpx_mock.add_response(json=build_two_result_response(*case.response_fields))

    async with Client(discovery_server) as client:
        result = await client.call_tool(case.tool_name, case.arguments)

    request = httpx_mock.get_requests()[0]
    assert request.url.path == case.expected_path

    # Compared as a whole so a failure reports every misrouted argument at once
    sent_params = {name: request.url.params.get(name) for name in case.expected_provider_params}
    assert sent_params == case.expected_provider_params

    for name in case.forbidden_params:
        assert name not in request.url.params

    payload = result.structured_content
    assert len(payload["results"]) == REQUESTED_MAX_RESULTS
    assert payload["results"][0]["media_type"] == case.expected_media_type
    assert payload["provider"] == PROVIDER_NAME


# =============================================================================
# Validation surfaced through the registered tools
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", SEARCH_TOOL_NAMES)
async def test_search_tools_reject_blank_query(discovery_server, tool_name: str):
    """Test that a blank query is rejected before any provider call is made."""
    async with Client(discovery_server) as client:
        with pytest.raises(ToolError, match="query must be a non-empty string"):
            await client.call_tool(tool_name, {"query": "   "})
