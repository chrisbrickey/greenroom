"""Categorization tools for the greenroom MCP server."""

from typing import Dict, Any, List

from fastmcp import FastMCP, Context

from greenroom.config import GENRE_ID, HAS_FILMS, HAS_TV_SHOWS, Mood, GENRE_MOOD_MAP
from greenroom.utils import create_empty_categorized_dict
from greenroom.services.protocols import MediaService
from greenroom.services.tmdb.service import TMDBService


__all__ = ["register_genre_tools", "fetch_genres"]


def register_genre_tools(mcp: FastMCP) -> None:
    """Register all genre-related tools with the MCP server and TMDB service."""

    service = TMDBService()

    @mcp.tool()
    def list_genres() -> Dict[str, Any]:
        """
        List all available entertainment genres across media types and providers.

        Returns:
            Dictionary mapping genre names to their properties:
            {
                "Documentary": {
                    "id": 99,
                    "has_films": true,
                    "has_tv_shows": true
                },
                "Action": {
                    "id": 28,
                    "has_films": true,
                    "has_tv_shows": false
                },
                ...
            }
        """

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return fetch_genres(service)

    @mcp.tool()
    async def list_genres_simplified(ctx: Context) -> str:
        """
        Get a simplified list of available genre names.

        Uses LLM sampling to extract genre names from the full genre data,
        returning a clean, formatted list without IDs or media type flags.
        Falls back to direct extraction if sampling is not supported.

        Returns:
            A formatted string containing the sorted list of genre names.

        Raises:
            Sampling errors are logged and result in fallback to direct key extraction.
        """

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await simplify_genres(ctx, service)

    @mcp.tool()
    async def categorize_genres(ctx: Context) -> Dict[str, List[str]]:
        """
        Categorize all available genres by mood/tone.

        Groups entertainment genres into mood categories (Dark, Light, Serious, Fun)
        using a hybrid approach: hardcoded mappings for common genres with LLM-based
        categorization for edge cases and unknown genres.

        Returns:
            Dictionary mapping mood categories to lists of genre names:
            {
                "Dark": ["Horror", "Thriller", "Crime", "Mystery"],
                "Light": ["Comedy", "Family", "Kids", "Animation", "Romance"],
                "Serious": ["Documentary", "History", "War", "Drama"],
                "Fun": ["Action", "Adventure", "Fantasy", "Science Fiction"],
                "Other": ["Western", "Film Noir"]
            }
        """

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await categorize_all_genres(ctx, service)

# =============================================================================
# Helper Methods (extracted from tools to ease unit testing)
# =============================================================================

def fetch_genres(service: MediaService) -> Dict[str, Any]:
    """Fetch genres from the service and transform to dict format."""

    # Get genres from service
    genre_list = service.get_genres()

    # Transform to the expected dict format for backward compatibility
    return {
        genre.name: {
            GENRE_ID: genre.id,
            HAS_FILMS: genre.has_films,
            HAS_TV_SHOWS: genre.has_tv_shows
        }
        for genre in genre_list.genres
    }

async def simplify_genres(ctx: Context, service: MediaService) -> str:
    """Encapsulates the genre simplification logic."""

    # Fetch all genre data
    genres = fetch_genres(service)

    try:
        # Use LLM sampling to format the response
        # Calls the agent again with new prompt to reformat the response before returning it to the user
        response = await ctx.sample(
            messages=f"Extract just the genre names from this data and return as a simple sorted comma-separated list:\n{genres}",
            system_prompt="You are a data formatter. Return only a clean, sorted list of genre names, nothing else.",
            temperature=0.0,  # Deterministic output
            max_tokens=500
        )
        return response.text

    except Exception as e:
        # Catch broad exception because we don't know the specific exception type
        # raised when sampling is not supported by the client
        await ctx.warning(f"Sampling failed ({type(e).__name__}: {e}), using fallback")
        return ", ".join(sorted(genres.keys()))


async def categorize_all_genres(ctx: Context, service: MediaService) -> Dict[str, List[str]]:
    """Encapsulates the genre categorization logic."""

    # Fetch all genres
    genres = fetch_genres(service)

    # Initialize category buckets using helper function
    categorized = create_empty_categorized_dict()

    # Categorize each genre
    for genre_name in sorted(genres.keys()):
        mood = await _categorize_single_genre(genre_name, ctx)
        if mood in categorized:
            categorized[mood].append(genre_name)

    return categorized

async def _categorize_single_genre(genre_name: str, ctx: Context) -> str:
    """
    Categorize a single genre using hybrid approach:
    First checks hardcoded mappings, then falls back to LLM sampling for unknown genres.
    """

    # Check hardcoded mapping first
    if genre_name in GENRE_MOOD_MAP:
        return GENRE_MOOD_MAP[genre_name]

    # Fall back to LLM sampling for unknown genres
    try:
        response = await ctx.sample(
            messages=f"Categorize the genre '{genre_name}' into exactly one of these moods: Dark, Light, Serious, or Fun. Respond with only the single mood word, nothing else.",
            system_prompt="You are a genre categorization system. Classify genres by mood/tone:\n- Dark: suspenseful, scary, intense\n- Light: uplifting, cheerful, entertaining\n- Serious: educational, thought-provoking, heavy topics\n- Fun: exciting, adventurous, escapist\nRespond with only one word.",
            temperature=0.0,
            max_tokens=10
        )

        # Normalize and validate the response
        mood = response.text.strip()
        if mood in [m.value for m in Mood]:
            return mood

    except Exception as e:
        # Log warning if sampling fails
        await ctx.warning(f"LLM categorization failed for '{genre_name}' ({type(e).__name__}: {e})")

    # Default fallback: categorize as "Other" if we can't determine
    return Mood.OTHER.value
