"""Utility helper functions for the greenroom MCP server."""

from greenroom.config import Mood


def create_empty_categorized_dict() -> dict[str, list[str]]:
    """
    Create empty categorized dictionary structure for genre categorization.

    Dynamically constructs the structure by looping over all Mood enum values,
    ensuring the dict stays in sync with the enum definition.

    Returns:
        Dictionary with mood categories as keys and empty lists as values.
        Used as the starting structure for categorizing genres by mood.

    Example:
        >>> result = create_empty_categorized_dict()
        >>> result
        {'Dark': [], 'Light': [], 'Serious': [], 'Fun': [], 'Other': []}
    """
    return {mood.value: [] for mood in Mood}
