"""TypedDict definitions for tool return schemas."""

from __future__ import annotations

from typing import TypedDict


class MediaResultDict(TypedDict):
    """Schema for a single media result returned by discovery tools."""
    id: str
    media_type: str
    title: str
    date: str | None
    rating: float | None
    description: str | None
    genre_ids: list[int] | None


class DiscoveryResultDict(TypedDict):
    """Schema for paginated discovery results returned by discovery tools."""
    results: list[MediaResultDict]
    total_results: int
    page: int
    total_pages: int
    provider: str


class GenrePropertiesDict(TypedDict):
    """Schema for genre properties returned by genre tools."""
    id: int
    has_films: bool
    has_tv_shows: bool


class LLMResponseEntryDict(TypedDict):
    """Schema for a single LLM response in a comparison."""
    source: str
    text: str | None
    error: str | None
    length: int


class LLMComparisonResultDict(TypedDict):
    """Schema for the full LLM comparison result."""
    prompt: str
    responses: list[LLMResponseEntryDict]
