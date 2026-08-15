"""Tests for the shared parameter validation in discovery/validation.py.

These exercise validation methods directly: no provider, no network, no MCP server.
"""

import pytest

from greenroom.services.media_limits import MAX_RESULTS_MAX, MAX_RESULTS_MIN
from greenroom.tools.discovery.validation import (
    VALID_SORT_OPTIONS,
    validate_discovery_params,
)

# --------------
# Fixtures
# --------------

# Stated once so every assertion below moves together when that policy changes
MIN_YEAR = 1900
BELOW_MIN_YEAR = MIN_YEAR - 1
MIN_PAGE = 1
YEAR_MESSAGE = f"year must be {MIN_YEAR} or later"
PAGE_MESSAGE = f"page must be {MIN_PAGE} or greater"
MAX_RESULTS_RANGE_MESSAGE = (
    f"max_results must be between {MAX_RESULTS_MIN} and {MAX_RESULTS_MAX}"
)
LANGUAGE_MESSAGE = "language must be a 2-character ISO 639-1 code"
SORT_BY_MESSAGE = "sort_by must be one of"

# Codes rejected as malformed: wrong length, or non-alphabetic characters
MALFORMED_LANGUAGE_CODES = ["", "e", "eng", "english", "e1", "12", "e-"]

# One wholly valid call per flow, so each test can override the single field it exercises.
VALID_DISCOVERY_PARAMS = {
    "year": 2024,
    "page": 1,
    "max_results": MAX_RESULTS_MAX,
    "language": "en",
    "sort_by": "popularity.desc",
}

# --------------
# Helpers
# --------------

def discovery_params(**overrides):
    """Build a valid discovery parameter set with the given fields replaced."""
    return {**VALID_DISCOVERY_PARAMS, **overrides}


# -------------------------
# Tests for discovery flow
# -------------------------

def test_accepts_fully_populated_valid_discovery_params():
    """Every filter supplied and valid is accepted."""
    validate_discovery_params(**VALID_DISCOVERY_PARAMS)


def test_accepts_omitted_optional_discovery_filters():
    """The optional filters are all independently skippable."""
    validate_discovery_params(**discovery_params(year=None, language=None, sort_by=None))


@pytest.mark.parametrize("year", [BELOW_MIN_YEAR, 0, -1])
def test_rejects_discovery_year_before_catalog_start(year):
    """Years earlier than the catalog floor are rejected."""
    with pytest.raises(ValueError, match=YEAR_MESSAGE):
        validate_discovery_params(**discovery_params(year=year))


@pytest.mark.parametrize("year", [MIN_YEAR, 2024, None])
def test_accepts_discovery_year_at_or_after_catalog_start(year):
    """The floor itself is accepted, as is omitting the filter."""
    validate_discovery_params(**discovery_params(year=year))


@pytest.mark.parametrize("page", [0, -1, -100])
def test_rejects_non_positive_discovery_page(page):
    """Pagination is 1-indexed, so zero and negatives are rejected."""
    with pytest.raises(ValueError, match=PAGE_MESSAGE):
        validate_discovery_params(**discovery_params(page=page))


@pytest.mark.parametrize("page", [MIN_PAGE, 2, 500])
def test_accepts_positive_discovery_page(page):
    """The first page and any page beyond it are accepted."""
    validate_discovery_params(**discovery_params(page=page))


@pytest.mark.parametrize("max_results", [MAX_RESULTS_MIN, MAX_RESULTS_MAX])
def test_accepts_discovery_max_results_at_the_bounds(max_results: int) -> None:
    """Both bounds are inclusive, so every count between them is accepted too."""
    validate_discovery_params(**discovery_params(max_results=max_results))


@pytest.mark.parametrize("max_results", [MAX_RESULTS_MIN - 1, MAX_RESULTS_MAX + 1])
def test_rejects_discovery_max_results_outside_the_bounds(max_results: int) -> None:
    """One step past either bound is rejected."""
    with pytest.raises(ValueError, match=MAX_RESULTS_RANGE_MESSAGE):
        validate_discovery_params(**discovery_params(max_results=max_results))


@pytest.mark.parametrize("language", ["en", "es", "fr", None])
def test_accepts_valid_language_code(language):
    """Two-letter alphabetic codes are accepted, as is omitting the filter."""
    validate_discovery_params(**discovery_params(language=language))


def test_accepts_uppercase_language_code():
    """Case is not currently enforced on language codes."""
    validate_discovery_params(**discovery_params(language="EN"))


@pytest.mark.parametrize("language", MALFORMED_LANGUAGE_CODES)
def test_rejects_malformed_language_code(language):
    """Codes of the wrong length or with non-alphabetic characters are rejected."""
    with pytest.raises(ValueError, match=LANGUAGE_MESSAGE):
        validate_discovery_params(**discovery_params(language=language))


@pytest.mark.parametrize("sort_by", VALID_SORT_OPTIONS)
def test_accepts_every_supported_sort_option(sort_by):
    """Every option the tools advertise is accepted by the check that guards them."""
    validate_discovery_params(**discovery_params(sort_by=sort_by))


def test_accepts_omitted_sort_by():
    """Omitting the sort order is accepted; the provider supplies a default."""
    validate_discovery_params(**discovery_params(sort_by=None))


@pytest.mark.parametrize(
    "sort_by",
    ["unknown.desc", "popularity", "POPULARITY.DESC", "name.asc", "popularity.sideways", ""],
)
def test_rejects_unsupported_sort_option(sort_by):
    """Sort orders outside the supported vocabulary are rejected."""
    with pytest.raises(ValueError, match=SORT_BY_MESSAGE):
        validate_discovery_params(**discovery_params(sort_by=sort_by))
