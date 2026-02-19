"""TypedDict definitions for tool return types."""

from typing import TypedDict


class MediaResultDict(TypedDict):
    id: str
    media_type: str
    title: str
    date: str | None
    rating: float | None
    description: str | None
    genre_ids: list[int] | None


class DiscoveryResultDict(TypedDict):
    results: list[MediaResultDict]
    total_results: int
    page: int
    total_pages: int
    provider: str


class GenrePropertiesDict(TypedDict):
    id: int
    has_films: bool
    has_tv_shows: bool


class LLMResponseEntryDict(TypedDict):
    source: str
    text: str | None
    error: str | None
    length: int


class LLMComparisonResultDict(TypedDict):
    prompt: str
    responses: list[LLMResponseEntryDict]
