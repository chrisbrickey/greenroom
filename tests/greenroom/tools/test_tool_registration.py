"""Tests that every tool is registered with the MCP server and wired correctly.

These tests cover only the tool registration layer: method names of the actual FastMCP
tools, their input parameter schemas, and the arguments that each tool forwards to its delegates.

The delegate methods, which can be called directly in tests without spinning up an MCP server,
contain the domain logic for each tool and those methods are comprehensively tested elsewhere.
"""

import json
import re
import pytest
from dataclasses import dataclass, field
from typing import Any
from fastmcp import Client, FastMCP
from fastmcp.client.sampling import SamplingMessage, SamplingParams
from fastmcp.exceptions import ToolError

from greenroom.tools import register_all_tools
from greenroom.tools.agent_tools import register_agent_tools
from greenroom.tools.discovery import register_all_discovery_tools
from greenroom.tools.genre_tools import register_genre_tools
from greenroom.config import Mood
from greenroom.models.media_types import MEDIA_TYPE_FILM, MEDIA_TYPE_TELEVISION
from greenroom.services.media_limits import DISCOVER_MAX_RESULTS, SEARCH_MAX_RESULTS


FASTMCP_RESULT_KEY = "result" # the key under which bare values are nested when using FastMCP
PROVIDER_NAME = "TMDB"
TEST_API_KEY = "test_api_key"
FILM_QUERY = "Test Film"


# =============================================================================
# Servers, one per registration function
# =============================================================================


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
# Registration and exposed schema
# =============================================================================

COMPARISON_PARAMETERS = ["prompt", "temperature", "max_tokens"]
COMPARISON_TEMPERATURE = 0.7
COMPARISON_MAX_TOKENS = 500

DISCOVERY_PARAMETERS = ["genre_id", "year", "language", "sort_by", "page", "max_results"]
SEARCH_PARAMETERS = ["query", "year", "display_language", "page", "max_results"]
FIRST_PAGE = 1
DISCOVERY_DEFAULTS: dict[str, Any] = {"page": FIRST_PAGE, "max_results": DISCOVER_MAX_RESULTS}
SEARCH_DEFAULTS: dict[str, Any] = {"page": FIRST_PAGE, "max_results": SEARCH_MAX_RESULTS}


@dataclass(frozen=True)
class SchemaCase:
    """A registered tool paired with the schema it is expected to publish.

    Attributes:
        tool_name: Name the tool is registered under
        server_fixture: Fixture supplying a server with this tool registered
        expected_parameters: Parameter names the tool advertises, in order
        expected_required: Parameter names the tool marks as required
        expected_defaults: Default value the tool advertises per parameter
    """
    tool_name: str
    server_fixture: str
    expected_parameters: list[str]
    expected_required: list[str]
    expected_defaults: dict[str, Any]


# Every tool the project registers. A tool missing from this list fails
# test_every_registered_tool_is_covered, so new tools cannot skip this layer.
SCHEMA_CASES = [
    SchemaCase(
        tool_name="discover_films",
        server_fixture="discovery_server",
        expected_parameters=DISCOVERY_PARAMETERS,
        expected_required=[],
        expected_defaults=DISCOVERY_DEFAULTS,
    ),
    SchemaCase(
        tool_name="discover_television",
        server_fixture="discovery_server",
        expected_parameters=DISCOVERY_PARAMETERS,
        expected_required=[],
        expected_defaults=DISCOVERY_DEFAULTS,
    ),
    SchemaCase(
        tool_name="search_films",
        server_fixture="discovery_server",
        expected_parameters=SEARCH_PARAMETERS,
        expected_required=["query"],
        expected_defaults=SEARCH_DEFAULTS,
    ),
    SchemaCase(
        tool_name="list_genres",
        server_fixture="genre_server",
        expected_parameters=[],
        expected_required=[],
        expected_defaults={},
    ),
    # The Context parameter is supplied by the framework, so it stays off the
    # published schema and agents see a tool that takes no arguments
    SchemaCase(
        tool_name="list_genres_simplified",
        server_fixture="genre_server",
        expected_parameters=[],
        expected_required=[],
        expected_defaults={},
    ),
    SchemaCase(
        tool_name="categorize_genres",
        server_fixture="genre_server",
        expected_parameters=[],
        expected_required=[],
        expected_defaults={},
    ),
    SchemaCase(
        tool_name="compare_llm_responses",
        server_fixture="agent_server",
        expected_parameters=COMPARISON_PARAMETERS,
        expected_required=["prompt"],
        expected_defaults={
            "temperature": COMPARISON_TEMPERATURE,
            "max_tokens": COMPARISON_MAX_TOKENS,
        },
    ),
]

# Tools each registration function is expected to contribute, stated separately
# from SCHEMA_CASES so that a tool added to neither list is still caught
REGISTRATION_CASES = [
    ("discovery_server", {"discover_films", "discover_television", "search_films"}),
    ("genre_server", {"list_genres", "list_genres_simplified", "categorize_genres"}),
    ("agent_server", {"compare_llm_responses"}),
]

REGISTRATION_CASE_IDS = [server_fixture for server_fixture, _ in REGISTRATION_CASES]


def case_id(case: SchemaCase) -> str:
    """Name each parametrized case after the tool it exercises."""
    return case.tool_name


@pytest.mark.asyncio
@pytest.mark.parametrize("server_fixture,expected_tool_names", REGISTRATION_CASES, ids=REGISTRATION_CASE_IDS)
async def test_registration_function_exposes_expected_tools(
    request,
    server_fixture: str,
    expected_tool_names: set[str]
):
    """Test that each registration function exposes exactly the tools it owns.

    Compared exactly rather than as a subset so that a tool dropped from a
    registration function, or one registered by surprise, both fail here.
    """
    server = request.getfixturevalue(server_fixture)
    tools = await server.get_tools()

    assert set(tools) == expected_tool_names


@pytest.mark.asyncio
async def test_every_registered_tool_is_covered(complete_server):
    """Test that no tool reaches agents without a case in this file."""
    tools = await complete_server.get_tools()
    assert set(tools) == {case.tool_name for case in SCHEMA_CASES}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SCHEMA_CASES, ids=case_id)
async def test_tool_exposes_expected_parameters(request, case: SchemaCase):
    """Test that each tool advertises its parameters and marks the right ones required."""
    server = request.getfixturevalue(case.server_fixture)
    tools = await server.get_tools()
    schema = tools[case.tool_name].parameters

    assert list(schema["properties"]) == case.expected_parameters
    assert schema.get("required", []) == case.expected_required


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SCHEMA_CASES, ids=case_id)
async def test_tool_advertises_expected_defaults(request, case: SchemaCase):
    """Test the defaults an agent sees on the published schema."""
    server = request.getfixturevalue(case.server_fixture)
    tools = await server.get_tools()
    properties = tools[case.tool_name].parameters["properties"]

    advertised = {name: properties[name]["default"] for name in case.expected_defaults}
    assert advertised == case.expected_defaults


# ================================================
# Argument routing through the registered tools
# ================================================

# Distinct values so that a mix-up between two arguments changes the outgoing request
REQUESTED_GENRE_ID = 28
REQUESTED_YEAR = 2001
REQUESTED_LANGUAGE = "es"
REQUESTED_SORT_BY = "vote_average.desc"
REQUESTED_PAGE = 2
REQUESTED_MAX_RESULTS = 1

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
        expected_path: Provider URL path the tool is expected to call
        expected_provider_params: Provider query params the arguments map onto
        expected_media_type: Media type the returned results carry
        response_fields: Provider title and date field names for this media type
        forbidden_params: Provider query params this tool must never send
    """
    tool_name: str
    arguments: dict[str, Any]
    expected_path: str
    expected_provider_params: dict[str, str]
    expected_media_type: str
    response_fields: tuple[str, str]
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


def expected_search_params(query: str, year_param: str) -> dict[str, str]:
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
        expected_path="/3/discover/movie",
        expected_provider_params={**SHARED_DISCOVERY_PARAMS, "primary_release_year": str(REQUESTED_YEAR)},
        expected_media_type=MEDIA_TYPE_FILM,
        response_fields=FILM_RESPONSE_FIELDS,
    ),
    ToolCase(
        tool_name="discover_television",
        arguments=DISCOVERY_ARGUMENTS,
        expected_path="/3/discover/tv",
        expected_provider_params={**SHARED_DISCOVERY_PARAMS, "first_air_date_year": str(REQUESTED_YEAR)},
        expected_media_type=MEDIA_TYPE_TELEVISION,
        response_fields=TELEVISION_RESPONSE_FIELDS,
    ),
    ToolCase(
        tool_name="search_films",
        arguments=build_search_arguments(FILM_QUERY),
        expected_path="/3/search/movie",
        expected_provider_params=expected_search_params(FILM_QUERY, "primary_release_year"),
        expected_media_type=MEDIA_TYPE_FILM,
        response_fields=FILM_RESPONSE_FIELDS,
        forbidden_params=DISCOVERY_ONLY_PARAMS,
    ),
]

# Split by flow because these flows use different parameters
DISCOVERY_TOOL_NAMES = [case.tool_name for case in TOOL_CASES if "sort_by" in case.arguments]
SEARCH_TOOL_NAMES = [case.tool_name for case in TOOL_CASES if "query" in case.arguments]


def build_two_result_response(title_field: str, date_field: str) -> dict[str, Any]:
    """Build a provider response with two results, so max_results truncation is observable.

    Args:
        title_field: Provider title field name ("title" or "name")
        date_field: Provider date field name ("release_date" or "first_air_date")

    Returns:
        Dictionary shaped like a TMDB content response
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


def discovery_case_id(case: ToolCase) -> str:
    """Name each parametrized case after the tool it exercises."""
    return case.tool_name


@pytest.mark.asyncio
@pytest.mark.parametrize("case", TOOL_CASES, ids=discovery_case_id)
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
# Routing through the registered genre tools
# =============================================================================

FILM_GENRE_LIST_URL = re.compile(r".*/genre/movie/list.*")
TELEVISION_GENRE_LIST_URL = re.compile(r".*/genre/tv/list.*")

FILM_ONLY_GENRE = "Sample Film Genre"
SHARED_GENRE = "Sample Shared Genre"
TELEVISION_ONLY_GENRE = "Sample Television Genre"

FILM_ONLY_GENRE_ID = 701
SHARED_GENRE_ID = 702
TELEVISION_ONLY_GENRE_ID = 703

FILM_GENRE_RESPONSE: dict[str, Any] = {
    "genres": [
        {"id": FILM_ONLY_GENRE_ID, "name": FILM_ONLY_GENRE},
        {"id": SHARED_GENRE_ID, "name": SHARED_GENRE},
    ]
}

TELEVISION_GENRE_RESPONSE: dict[str, Any] = {
    "genres": [
        {"id": SHARED_GENRE_ID, "name": SHARED_GENRE},
        {"id": TELEVISION_ONLY_GENRE_ID, "name": TELEVISION_ONLY_GENRE},
    ]
}

EXPECTED_GENRE_PROPERTIES: dict[str, dict[str, Any]] = {
    FILM_ONLY_GENRE: {"id": FILM_ONLY_GENRE_ID, "has_films": True, "has_tv_shows": False},
    SHARED_GENRE: {"id": SHARED_GENRE_ID, "has_films": True, "has_tv_shows": True},
    TELEVISION_ONLY_GENRE: {"id": TELEVISION_ONLY_GENRE_ID, "has_films": False, "has_tv_shows": True},
}

# None of the test genres appear in the hardcoded mood map, so every one of them
# takes the sampling path and the Context wiring stays observable
SAMPLED_MOOD = Mood.DARK.value
SIMPLIFIED_GENRE_REPLY = "sample-genre-one, sample-genre-two"


@pytest.fixture
def genre_endpoints(httpx_mock) -> None:
    """Answer both provider genre endpoints with distinguishable payloads."""
    httpx_mock.add_response(url=FILM_GENRE_LIST_URL, json=FILM_GENRE_RESPONSE)
    httpx_mock.add_response(url=TELEVISION_GENRE_LIST_URL, json=TELEVISION_GENRE_RESPONSE)


@pytest.mark.asyncio
async def test_list_genres_returns_combined_provider_genres(genre_server, genre_endpoints, httpx_mock):
    """Test that the tool reaches both provider genre endpoints and returns the merged result."""
    async with Client(genre_server) as client:
        result = await client.call_tool("list_genres", {})

    requested_paths = {request.url.path for request in httpx_mock.get_requests()}
    assert requested_paths == {"/3/genre/movie/list", "/3/genre/tv/list"}

    assert result.structured_content == EXPECTED_GENRE_PROPERTIES


@pytest.mark.asyncio
async def test_list_genres_simplified_returns_sampled_reply(genre_server, genre_endpoints):
    """Test that the tool passes its Context to the delegate and returns what sampling produced.

    A tool registered without its Context reaching ctx.sample would silently fall
    back to direct extraction, so the sampled reply is what proves the wiring.
    """
    recorder = SamplingRecorder(reply=SIMPLIFIED_GENRE_REPLY)

    async with Client(genre_server, sampling_handler=recorder) as client:
        result = await client.call_tool("list_genres_simplified", {})

    assert len(recorder.requests) == 1

    # The genre data fetched from the provider is what the tool asked about
    assert SHARED_GENRE in sampled_prompt(recorder.requests[0])

    assert result.structured_content[FASTMCP_RESULT_KEY] == SIMPLIFIED_GENRE_REPLY


@pytest.mark.asyncio
async def test_categorize_genres_returns_mood_buckets(genre_server, genre_endpoints):
    """Test that the tool routes every fetched genre through Context and returns mood buckets."""
    recorder = SamplingRecorder(reply=SAMPLED_MOOD)

    async with Client(genre_server, sampling_handler=recorder) as client:
        result = await client.call_tool("categorize_genres", {})

    # One sampling request per genre the provider returned
    assert len(recorder.requests) == len(EXPECTED_GENRE_PROPERTIES)

    expected = {
        Mood.DARK.value: sorted(EXPECTED_GENRE_PROPERTIES),
        Mood.LIGHT.value: [],
        Mood.SERIOUS.value: [],
        Mood.FUN.value: [],
        Mood.OTHER.value: [],
    }
    assert result.structured_content == expected


# =============================================================================
# Argument routing through the registered agent comparison tool
# =============================================================================

ALTERNATIVE_LLM_URL = re.compile(r".*/api/generate")
ALTERNATIVE_REPLY = "sample-alternative-text"
EMPTY_PROMPT = "   "
REQUESTED_MAX_TOKENS = 42
REQUESTED_PROMPT = "sample-prompt"
RESAMPLE_REPLY = "sample-resampled-text"
REQUESTED_TEMPERATURE = 0.1

COMPARISON_ARGUMENTS: dict[str, Any] = {
    "prompt": REQUESTED_PROMPT,
    "temperature": REQUESTED_TEMPERATURE,
    "max_tokens": REQUESTED_MAX_TOKENS,
}

@pytest.fixture
def alternative_llm(httpx_mock) -> None:
    """Answer the alternative provider so the comparison completes offline."""
    httpx_mock.add_response(url=ALTERNATIVE_LLM_URL, json={"response": ALTERNATIVE_REPLY})


@pytest.mark.asyncio
async def test_compare_tool_forwards_arguments_to_both_llms(agent_server, alternative_llm, httpx_mock):
    """Test that the tool routes its arguments onto both sides of the comparison."""
    recorder = SamplingRecorder(reply=RESAMPLE_REPLY)

    async with Client(agent_server, sampling_handler=recorder) as client:
        result = await client.call_tool("compare_llm_responses", COMPARISON_ARGUMENTS)

    # Assert resampled side receives the arguments through Context
    sampling_request = recorder.requests[0]
    assert sampled_prompt(sampling_request) == REQUESTED_PROMPT
    assert sampling_request.temperature == REQUESTED_TEMPERATURE
    assert sampling_request.maxTokens == REQUESTED_MAX_TOKENS

    # Assert the alternative side receives the same arguments over HTTP
    sent_body = json.loads(httpx_mock.get_requests()[0].content)
    assert sent_body["prompt"] == REQUESTED_PROMPT
    assert sent_body["options"] == {
        "temperature": REQUESTED_TEMPERATURE,
        "num_predict": REQUESTED_MAX_TOKENS,
    }

    payload = result.structured_content
    assert payload["prompt"] == REQUESTED_PROMPT
    assert [entry["text"] for entry in payload["responses"]] == [RESAMPLE_REPLY, ALTERNATIVE_REPLY]


@pytest.mark.asyncio
async def test_compare_tool_applies_advertised_defaults(agent_server, alternative_llm, httpx_mock):
    """Test that omitted tuning arguments reach the providers as the advertised defaults."""
    recorder = SamplingRecorder(reply=RESAMPLE_REPLY)

    async with Client(agent_server, sampling_handler=recorder) as client:
        await client.call_tool("compare_llm_responses", {"prompt": REQUESTED_PROMPT})

    sampling_request = recorder.requests[0]
    assert sampling_request.temperature == COMPARISON_TEMPERATURE
    assert sampling_request.maxTokens == COMPARISON_MAX_TOKENS

    sent_body = json.loads(httpx_mock.get_requests()[0].content)
    assert sent_body["options"] == {
        "temperature": COMPARISON_TEMPERATURE,
        "num_predict": COMPARISON_MAX_TOKENS,
    }


# =============================================================================
# Validation surfaced through the registered tools
# =============================================================================

UNSUPPORTED_SORT_BY = "not-a-real-field.desc"
BLANK_QUERY = "   "


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", DISCOVERY_TOOL_NAMES)
async def test_tool_rejects_unsupported_sort_order(discovery_server, httpx_mock, tool_name: str):
    """Test that an invalid argument is rejected before any provider call is made."""
    async with Client(discovery_server) as client:
        with pytest.raises(ToolError, match="sort_by must be one of"):
            await client.call_tool(tool_name, {"sort_by": UNSUPPORTED_SORT_BY})


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", SEARCH_TOOL_NAMES)
async def test_search_tools_reject_blank_query(discovery_server, httpx_mock, tool_name: str):
    """Test that a blank query is rejected before any provider call is made."""
    async with Client(discovery_server) as client:
        with pytest.raises(ToolError, match="query must be a non-empty string"):
            await client.call_tool(tool_name, {"query": BLANK_QUERY})


@pytest.mark.asyncio
async def test_compare_tool_rejects_empty_prompt(agent_server, httpx_mock):
    """Test that an empty prompt is rejected before either LLM is called.

    No provider response is registered, so a call reaching one raises rather
    than going out to the network.
    """
    recorder = SamplingRecorder(reply=RESAMPLE_REPLY)

    async with Client(agent_server, sampling_handler=recorder) as client:
        with pytest.raises(ToolError, match="Prompt cannot be empty"):
            await client.call_tool("compare_llm_responses", {"prompt": EMPTY_PROMPT})

    assert recorder.requests == []
