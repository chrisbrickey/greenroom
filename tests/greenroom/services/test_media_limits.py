"""Tests for the constants in services/media_limits.py.

This is the one place the policy numbers are stated as literals. Every other
test derives its inputs from these constants, so a bound that moves is reported
here by name rather than as a ValueError inside a dozen unrelated tool tests.
"""

from greenroom.services.media_limits import (
    DISCOVER_MAX_RESULTS,
    MAX_RESULTS_MAX,
    MAX_RESULTS_MIN,
)

# This is a restriction set by a content provider, but we set it as a literal in these tests.
# The value in real life is tested in an external test that makes a network call to the provider.
SINGLE_PROVIDER_PAGE = 20


def test_floor_is_a_single_result() -> None:
    """The smallest count a caller may ask for is one."""

    assert MAX_RESULTS_MIN == 1


def test_ceiling_is_a_single_provider_page() -> None:
    """The most a caller may ask for is everything one page can hold."""

    assert MAX_RESULTS_MAX == SINGLE_PROVIDER_PAGE


def test_advertised_default_fills_a_page() -> None:
    """The default the tools publish returns everything one call can fetch."""

    assert DISCOVER_MAX_RESULTS == SINGLE_PROVIDER_PAGE
