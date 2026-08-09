"""Shaping of domain media models into the payload the tools return to the agent.

Shared by the discover and search flows, which return the same envelope.
"""

from greenroom.models.media import MediaList
from greenroom.models.responses import DiscoveryResultDict
from greenroom.services.protocols import MediaService


def format_media_list(media_list: MediaList, media_service: MediaService) -> DiscoveryResultDict:
    """Format MediaList for agent consumption.

    Args:
        media_list: MediaList from service
        media_service: Media service instance for getting provider name

    Returns:
        Dictionary formatted for agent
    """

    return {
        "results": [
            {
                "id": media.id,
                "media_type": media.media_type,
                "title": media.title,
                "date": media.date.isoformat() if media.date else None,
                "rating": media.rating,
                "description": media.description,
                "genre_ids": media.genre_ids
            }
            for media in media_list.results
        ],
        "total_results": media_list.total_results,
        "page": media_list.page,
        "total_pages": media_list.total_pages,
        "provider": media_service.get_provider_name()
    }
