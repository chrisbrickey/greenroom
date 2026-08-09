"""Translation of caller arguments into TMDB query parameters.

Outbound half of the TMDB anti-corruption layer: converts the provider-agnostic
arguments supplied by the tools into the parameter names and vocabulary that the
TMDB endpoints expect.
"""

from greenroom.services.tmdb.config import TMDBMediaConfig


# A TMDB query parameter mapping. Values are limited to the scalar types that
# TMDB accepts in a query string.
TMDBParams = dict[str, str | int | bool]

# Sort order applied when the caller does not request one
DEFAULT_SORT_ORDER = "popularity.desc"

# Provider-agnostic sort field exposed by the tools. TMDB names its date field
# differently per media type, so this is translated before the request is sent.
GENERIC_DATE_SORT_FIELD = "date"


def build_discover_params(
    config: TMDBMediaConfig,
    genre_id: int | None,
    year: int | None,
    language: str | None,
    sort_by: str | None,
    page: int
) -> TMDBParams:
    """Build query parameters for the TMDB discover endpoints.

    Args:
        config: TMDB media configuration
        genre_id: Optional genre filter
        year: Optional year filter
        language: Optional original-language filter
        sort_by: Sort order (None defaults to "popularity.desc")
        page: Page number

    Returns:
        Dictionary of TMDB query parameters
    """

    params: TMDBParams = {
        "sort_by": _to_provider_sort_order(sort_by, config),
        "page": page,
        "include_adult": False, # Exclude pornographic content
        "include_video": False  # Exclude video-only content
    }

    if genre_id is not None:
        params["with_genres"] = genre_id

    if year is not None:
        params[config.year_param] = year

    if language is not None:
        params["with_original_language"] = language

    return params


def build_search_params(
    config: TMDBMediaConfig,
    query: str,
    year: int | None,
    display_language: str | None,
    page: int
) -> TMDBParams:
    """Build query parameters for the TMDB search endpoints.

    TMDB provides search endpoints (searching for a single title) that are
    distinct from its endpoints for retrieving a list of media based on filters.
    The different endpoints accept different sets of parameters
    so we use distinct helper functions to build the parameter sets.

    Args:
        config: TMDB media configuration
        query: Title text to search for
        year: Optional year filter
        display_language: Optional language for the returned title and overview
        page: Page number

    Returns:
        Dictionary of TMDB query parameters
    """

    params: TMDBParams = {
        "query": query,
        "page": page,
        "include_adult": False  # Exclude pornographic content
    }

    if year is not None:
        params[config.year_param] = year

    if display_language is not None:
        params["language"] = display_language

    return params


def _to_provider_sort_order(sort_by: str | None, config: TMDBMediaConfig) -> str:
    """Translate a provider-agnostic sort order into TMDB's vocabulary.

    The tools expose "date.asc" and "date.desc" so that callers need not know
    whether they are sorting films or television. TMDB rejects "date" and
    expects "release_date" for films and "first_air_date" for television.
    Every other sort order is already TMDB-native and passes through.

    Args:
        sort_by: Requested sort order, or None for the default
        config: TMDB media configuration supplying the date field name

    Returns:
        Sort order string accepted by the TMDB discover endpoints
    """

    if sort_by is None:
        return DEFAULT_SORT_ORDER

    field, separator, direction = sort_by.partition(".")
    if field == GENERIC_DATE_SORT_FIELD:
        return f"{config.date_sort_prefix}{separator}{direction}"

    return sort_by
