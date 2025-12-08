"""Film discovery tools for the greenroom MCP server."""

import json
import os
from typing import Dict, List, Any, Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError


# Pydantic model for TMDB film validation
class TMDBFilm(BaseModel):
    """TMDB API film structure with flexible field handling.

    Only 'id' is required - all other fields optional to handle:
    - Incomplete TMDB data
    - API changes/additions
    - Regional variations in data availability
    """
    id: int
    title: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    overview: Optional[str] = None
    genre_ids: Optional[List[int]] = Field(default_factory=list)


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register film discovery tools with the MCP server."""

    @mcp.tool()
    def discover_films(
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve films based on discovery criteria.

        Discovers films from TMDB based on optional filters like genre, release year,
        language, and sorting preferences. Returns essential metadata for each film
        including title, release date, ratings, and overview.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional release year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "release_date.desc",
                     "release_date.asc" (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": int,
                        "title": str (may be None),
                        "release_date": str in YYYY-MM-DD format (may be None),
                        "vote_average": float (may be None),
                        "overview": str (may be None),
                        "genre_ids": List[int] (may be empty)
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int
            }

        Raises:
            ValueError: If TMDB_API_KEY is not configured in environment, or if
                       invalid parameters provided (year < 1900, page < 1, etc.)
            RuntimeError: If TMDB API returns an HTTP error status or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return discover_films_from_tmdb(genre_id, year, language, sort_by, page, max_results)


def discover_films_from_tmdb(
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Encapsulates film discovery logic. See discover_films() for detailed documentation.
    """
    # Validate inputs
    _validate_discovery_params(genre_id, year, language, sort_by, page, max_results)

    # Get API key
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError(
            "TMDB_API_KEY not configured. "
            "Set TMDB_API_KEY in .env file. "
            "Get your key from https://www.themoviedb.org/settings/api"
        )

    # Build query parameters
    params = _build_discovery_params(api_key, genre_id, year, language, sort_by, page)

    # Call TMDB API
    base_url = "https://api.themoviedb.org/3"
    headers = {"accept": "application/json"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{base_url}/discover/movie",
                params=params,
                headers=headers
            )
            response.raise_for_status()

        data = response.json()

        # Extract and validate film data
        raw_results = data.get("results", [])
        validated_films = _filter_incomplete_films(raw_results)

        # Apply max_results limit
        limited_films = validated_films[:max_results]

        # Format response
        return _format_discovery_response(limited_films, data, page)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"TMDB API error: {e.response.status_code} - {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise ConnectionError(
            f"Failed to connect to TMDB API: {str(e)}"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"TMDB API returned invalid JSON: {str(e)}"
        ) from e


def _validate_discovery_params(
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int,
    max_results: int
) -> None:
    """Validate discovery parameters.

    Args:
        genre_id: TMDB genre ID (optional)
        year: Release year (optional)
        language: ISO 639-1 language code (optional)
        sort_by: Sort order string
        page: Page number for pagination
        max_results: Maximum number of results to return

    Raises:
        ValueError: If any parameter is invalid
    """
    if year is not None and year < 1900:
        raise ValueError("Year must be 1900 or later")

    if page < 1:
        raise ValueError("Page must be 1 or greater")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")

    valid_sort_options = [
        "popularity.desc", "popularity.asc",
        "vote_average.desc", "vote_average.asc",
        "release_date.desc", "release_date.asc"
    ]
    if sort_by not in valid_sort_options:
        raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")

    # Validate language code format (must be 2-character ISO 639-1 code)
    if language is not None:
        if not isinstance(language, str) or len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')")


def _build_discovery_params(
    api_key: str,
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int
) -> Dict[str, Any]:
    """Build TMDB API query parameters.

    Args:
        api_key: TMDB API key
        genre_id: TMDB genre ID (optional)
        year: Release year (optional)
        language: ISO 639-1 language code (optional)
        sort_by: Sort order string
        page: Page number for pagination

    Returns:
        Dictionary of query parameters for TMDB API
    """
    params = {
        "api_key": api_key,
        "sort_by": sort_by,
        "page": page,
        "include_adult": False,  # Exclude pornographic content
        "include_video": False   # Exclude video-only content
    }

    if genre_id is not None:
        params["with_genres"] = genre_id

    if year is not None:
        params["primary_release_year"] = year

    if language is not None:
        params["with_original_language"] = language

    return params


def _filter_incomplete_films(films_data: List[Dict[str, Any]]) -> List[TMDBFilm]:
    """
    Validate film data, skipping invalid entries.

    Only films with at least an 'id' field will be kept. This ensures we can
    always identify a film, even if other metadata is missing.

    Args:
        films_data: Raw film data from TMDB API

    Returns:
        List of validated TMDBFilm models (invalid entries are silently skipped)
    """
    valid_films = []
    for film in films_data:
        try:
            valid_films.append(TMDBFilm(**film))
        except ValidationError:
            # Skip films without even an 'id' field
            pass
    return valid_films


def _format_discovery_response(
    films: List[TMDBFilm],
    raw_data: Dict[str, Any],
    page: int
) -> Dict[str, Any]:
    """Format discovery response for return to user.

    Args:
        films: List of validated TMDBFilm models
        raw_data: Raw response data from TMDB API
        page: Current page number

    Returns:
        Formatted response dictionary with results and pagination metadata
    """
    return {
        "results": [
            {
                "id": film.id,
                "title": film.title,
                "release_date": film.release_date,
                "vote_average": film.vote_average,
                "overview": film.overview,
                "genre_ids": film.genre_ids or []
            }
            for film in films
        ],
        "total_results": raw_data.get("total_results", 0),
        "page": page,
        "total_pages": raw_data.get("total_pages", 0)
    }
