"""Base protocols for services."""

from typing import Any, Protocol, runtime_checkable
from greenroom.models.genre import GenreList
from greenroom.models.media import MediaList
from greenroom.models.media_types import MediaType


@runtime_checkable
class LLMClient(Protocol):
    """Protocol defining the interface for LLM API clients.

    Any LLM provider (Ollama, Groq, etc.) must implement this interface
    to be compatible with LLMService.
    """

    SERVICE_NAME: str

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> dict[str, Any]:
        """Make a generation request to the LLM API.

        Args:
            prompt: The prompt to send
            model: Model name/identifier
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            APITypeError: If response has unexpected Python type
            APIResponseError: If API returns an HTTP error
            APIConnectionError: If unable to connect to API
        """
        ...


@runtime_checkable
class MediaService(Protocol):
    """Protocol defining the unified interface for media services.

    Any provider (TMDB, IMDb, OMDb, etc.) must implement this interface to be
    compatible with the genre and media discovery tools.
    """

    async def get_genres(self) -> GenreList:
        """Fetch all available genres.

        Returns:
            GenreList with standardized Genre objects including media type availability

        Raises:
            APIResponseError: For service errors
            APIConnectionError: For network errors
        """
        ...

    async def get_media(
        self,
        media_type: MediaType,
        genre_id: int | None,
        year: int | None,
        language: str | None,
        sort_by: str | None,
        page: int,
        max_results: int
    ) -> MediaList:
        """Retrieve list of media matching the given criteria.

        Args:
            media_type: Type-safe group of media to discover
            genre_id: Filter on genre provided via genre tools, or None
            year: Filter on year of release, or None
            language: ISO 639-1 language code, or None
            sort_by: Sort order string that is provider-specific, or None
            page: Page number for pagination (1-indexed)
            max_results: Maximum number of results to return

        Returns:
            MediaList with standardized Media objects

        Raises:
            ValueError: For invalid parameters
            APIResponseError: For service errors
            APIConnectionError: For network errors
        """
        ...

    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'TMDB', 'IMDb')."""
        ...