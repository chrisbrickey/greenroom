"""TMDB API HTTP client."""

import json
import os
import httpx
from typing import Dict, Any


class TMDBClient:
    """HTTP client for interacting with The Movie Database (TMDB) API.

    Handles authentication, request construction, and error handling specific
    to the TMDB API.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    SERVICE_NAME = "TMDB"

    def __init__(self):
        """Initialize the TMDB client.

        Raises:
            ValueError: If TMDB_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("TMDB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "TMDB_API_KEY not configured. "
                "Set TMDB_API_KEY in .env file. "
                "Get your key from https://www.themoviedb.org/settings/api"
            )

    def get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GET request to TMDB API.

        Args:
            endpoint: API endpoint (e.g., "/discover/movie")
            params: Query parameters (API key will be added automatically)

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            RuntimeError: If TMDB API returns an HTTP error or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """
        # Add API key to parameters
        params["api_key"] = self.api_key
        headers = {"accept": "application/json"}

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}{endpoint}",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()

            result = response.json()
            if not isinstance(result, dict):
                raise RuntimeError(f"{self.SERVICE_NAME} API returned unexpected type: {type(result)}")
            return result

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"{self.SERVICE_NAME} API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ConnectionError(
                f"Failed to connect to {self.SERVICE_NAME} API: {str(e)}"
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"{self.SERVICE_NAME} API returned invalid JSON: {str(e)}"
            ) from e
