"""Shared validation of the parameters received by the tools from the agent.

These checks depend only on the caller's arguments. They should be independent
of the downstream service selected. These checks should apply to any media type
that the tools grow to cover.
"""


# Sort orders the discovery tools accept. These are provider-agnostic: the
# service translates them into the vocabulary of whichever provider it wraps.
VALID_SORT_OPTIONS = (
    "popularity.desc", "popularity.asc",
    "vote_average.desc", "vote_average.asc",
    "date.desc", "date.asc",
)

# Bounds enforced on the parameters callers supply.
MIN_YEAR = 1900
MIN_PAGE = 1
LANGUAGE_CODE_LENGTH = 2
MAX_RESULTS_MIN = 1
MAX_RESULTS_MAX = 100


def validate_discovery_params(
    *,
    year: int | None,
    page: int,
    max_results: int,
    language: str | None,
    sort_by: str | None
) -> None:
    """Validate the parameters accepted by the discovery tools.

    Raises:
        ValueError: If any parameter is invalid
    """

    _validate_year(year)
    _validate_page(page)
    _validate_max_results(max_results)
    _validate_language_code(language)
    _validate_sort_by(sort_by)


def _validate_year(year: int | None) -> None:
    """Reject years before the start of the catalog."""

    if year is not None and year < MIN_YEAR:
        raise ValueError(f"year must be {MIN_YEAR} or later")


def _validate_page(page: int) -> None:
    """Reject non-positive page numbers, since pagination is 1-indexed."""

    if page < MIN_PAGE:
        raise ValueError(f"page must be {MIN_PAGE} or greater")


def _validate_max_results(max_results: int) -> None:
    """Reject result counts outside the supported range."""

    if max_results < MAX_RESULTS_MIN or max_results > MAX_RESULTS_MAX:
        raise ValueError(f"max_results must be between {MAX_RESULTS_MIN} and {MAX_RESULTS_MAX}")


def _validate_language_code(language: str | None) -> None:
    """Reject anything that is not a 2-letter ISO 639-1 code."""

    if language is None:
        return

    if len(language) != LANGUAGE_CODE_LENGTH or not language.isalpha():
        raise ValueError(
            "language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')"
        )


def _validate_sort_by(sort_by: str | None) -> None:
    """Reject sort orders outside the supported vocabulary."""

    if sort_by is not None and sort_by not in VALID_SORT_OPTIONS:
        raise ValueError(f"sort_by must be one of: {', '.join(VALID_SORT_OPTIONS)}")
