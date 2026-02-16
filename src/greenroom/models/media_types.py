"""Media type constants and type definitions."""

from typing import Final, Literal

# String constants for media types
# These constants should be used instead of magic strings throughout the codebase
MEDIA_TYPE_FILM: Final = "film"
MEDIA_TYPE_TELEVISION: Final = "television"
MEDIA_TYPE_PODCAST: Final = "podcast"
MEDIA_TYPE_BOOK: Final = "book"
MEDIA_TYPE_MUSIC: Final = "music"
MEDIA_TYPE_GAME: Final = "game"


# Literal type for type checking
# This provides IDE autocomplete and mypy validation while remaining flexible
# Note: We use Literal instead of Enum for lighter weight and easier extensibility
MediaType = Literal[
    "film",
    "television",
    "podcast",
    "book",
    "music",
    "game",
]

# To add a new media type in the future:
# 1. Add a constant: MEDIA_TYPE_XXXXX = "xxxxx"
# 2. Add the string to the MediaType Literal union above
# 3. Add config to specific service's config_map if that service supports it
# 4. Create corresponding MCP tool (e.g., discover_xxxxx) if needed
