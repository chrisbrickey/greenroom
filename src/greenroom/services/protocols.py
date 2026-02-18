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

    def get_genres(self) -> GenreList:
        """Fetch all available genres.

        Returns:
            GenreList with standardized Genre objects including media type availability

        Raises:
            APIResponseError: For service errors
            APIConnectionError: For network errors
        """
        ...

    def get_media(
        self,
        media_type: MediaType,
        genre_id: int | None = None,
        year: int | None = None,
        language: str | None = None,
        sort_by: str | None = None,
        page: int = 1,
        max_results: int = 20
    ) -> MediaList:
        """Discover media matching the given criteria.

        Args:
            media_type: Type-safe group of media to discover
            genre_id: Optional filter on genre provided via genre tools
            year: Optional filter on year of release
            language: Optional ISO 639-1 language code
            sort_by: Optional sort order string that is provider-specific
            page: Page number for pagination (1-indexed, defaults to 1)
            max_results: Maximum number of results to return; defaults to 20

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