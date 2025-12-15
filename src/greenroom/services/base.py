"""Base protocol for media discovery services."""

from typing import Protocol, Optional
from greenroom.models.media import MediaList
from greenroom.models.media_types import MediaType


class MediaDiscoveryService(Protocol):
    """Protocol defining the interface for media discovery services.

    Any provider (TMDB, IMDb, OMDb, etc.) must implement this interface to be
    compatible with the discovery tools.
    """

    def discover(
        self,
        media_type: MediaType,
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        max_results: int = 20
    ) -> MediaList:
        """Discover media matching the given criteria.

        Args:
            media_type: Type-safe media type (use constants from media_types module)
            genre_id: Optional genre filter
            year: Optional year filter (release/air year)
            language: Optional ISO 639-1 language code
            sort_by: Sort order (provider-specific format, None uses provider default)
            page: Page number (1-indexed)
            max_results: Maximum results to return

        Returns:
            MediaList with standardized Media objects

        Raises:
            ValueError: For invalid parameters
            RuntimeError: For service errors
            ConnectionError: For network errors
        """
        ...

    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'TMDB', 'IMDb')."""
        ...
