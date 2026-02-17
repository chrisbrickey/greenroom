"""Custom exception hierarchy for the greenroom MCP server."""


class GreenroomError(Exception):
    """Base exception for all greenroom errors."""


class APIResponseError(GreenroomError):
    """HTTP errors, invalid JSON, or bad response bodies from external APIs."""


class APIConnectionError(GreenroomError):
    """Network or connectivity failures when calling external APIs."""


class APITypeError(GreenroomError):
    """Response had unexpected Python type after deserialization."""


class SamplingError(GreenroomError):
    """Errors during MCP ctx.sample() calls."""
