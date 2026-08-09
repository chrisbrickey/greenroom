"""Translation of TMDB media payloads into provider-agnostic domain models.

Inbound half of the TMDB anti-corruption layer. The discover and search
endpoints return the same payload shape, so both flows share this mapping.
"""

from datetime import date
from typing import Any

from pydantic import ValidationError

from greenroom.models.media import Media, MediaList
from greenroom.models.media_types import MediaType
from greenroom.services.tmdb.config import TMDBMediaConfig
from greenroom.services.tmdb.models import TMDBMediaItem


def to_media_list(
    data: dict[str, Any],
    config: TMDBMediaConfig,
    media_type: MediaType,
    page: int,
    max_results: int
) -> MediaList:
    """Convert a raw TMDB media payload into a standardized MediaList.

    Args:
        data: Parsed JSON body from a TMDB discover or search endpoint
        config: TMDB media configuration for the requested media type
        media_type: Type-safe media type to stamp on each result
        page: Page number that was requested, echoed back in the response
        max_results: Maximum number of results to keep

    Returns:
        MediaList with standardized Media objects
    """

    tmdb_items = _parse_items(data.get("results", []), config)
    standard_items = [_to_standard_media(item, config, media_type) for item in tmdb_items]

    return MediaList(
        results=standard_items[:max_results],
        total_results=data.get("total_results", 0),
        page=page,
        total_pages=data.get("total_pages", 0)
    )


def _parse_items(
    raw_results: list[dict[str, Any]],
    config: TMDBMediaConfig
) -> list[TMDBMediaItem]:
    """Validate raw TMDB items against the schema for their media type.

    Args:
        raw_results: Raw results array from the TMDB API
        config: TMDB media configuration supplying the model class

    Returns:
        List of validated models. Items that fail validation are skipped rather
        than failing the whole page, so one malformed entry cannot discard
        otherwise usable results.
    """

    valid_items: list[TMDBMediaItem] = []
    for item_data in raw_results:
        try:
            valid_items.append(config.model_class(**item_data))
        except ValidationError:
            # Skip items that don't match the schema (missing required fields)
            pass
    return valid_items


def _to_standard_media(
    tmdb_item: TMDBMediaItem,
    config: TMDBMediaConfig,
    media_type: MediaType
) -> Media:
    """Transform a validated TMDB item into the standard Media model.

    Title and date are read through config because TMDB names those fields
    differently for films and television.

    Args:
        tmdb_item: Validated TMDB model (TMDBFilm or TMDBTelevision)
        config: TMDB media configuration
        media_type: Type-safe media type

    Returns:
        Standard Media object with normalized field names
    """

    title: str | None = getattr(tmdb_item, config.title_field, None)
    raw_date: str | None = getattr(tmdb_item, config.date_field, None)

    return Media(
        id=str(tmdb_item.id),
        media_type=media_type,
        title=title or "",
        date=_parse_date(raw_date),
        rating=tmdb_item.vote_average,
        description=tmdb_item.overview,
        genre_ids=tmdb_item.genre_ids or []
    )


def _parse_date(date_str: str | None) -> date | None:
    """Parse a TMDB date string, treating unparseable values as absent.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Date object, or None if missing or malformed
    """

    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None
