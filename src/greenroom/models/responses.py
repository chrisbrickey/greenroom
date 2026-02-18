"""TypedDict definitions for tool return types."""

from typing import List, Optional, TypedDict


class MediaResultDict(TypedDict):
    id: str
    media_type: str
    title: str
    date: Optional[str]
    rating: Optional[float]
    description: Optional[str]
    genre_ids: Optional[List[int]]


class DiscoveryResultDict(TypedDict):
    results: List[MediaResultDict]
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
    text: Optional[str]
    error: Optional[str]
    length: int


class LLMComparisonResultDict(TypedDict):
    prompt: str
    responses: List[LLMResponseEntryDict]
