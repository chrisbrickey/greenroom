"""Ollama API HTTP client."""

import os
from typing import Dict, Any

import httpx

from greenroom.exceptions import APIConnectionError, APIResponseError, APITypeError, GreenroomError
from greenroom.services.llm.config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT


class OllamaClient:
    """
    HTTP client encapsulates transport-layer interaction
    with the Ollama API, including request construction
    and error handling specific to the Ollama API.
    """

    SERVICE_NAME = "Ollama"

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Make a generate request to Ollama API.

        Args:
            prompt: The prompt to send
            model: Ollama model name
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON response as a dictionary

        Raises:
            APITypeError: If response has unexpected Python type
            APIResponseError: If Ollama API returns an HTTP error
            APIConnectionError: If unable to connect to Ollama API
        """
        base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                response = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    }
                )
                response.raise_for_status()

                result = response.json()
                if not isinstance(result, dict):
                    raise APITypeError(f"{self.SERVICE_NAME} API returned unexpected type: {type(result)}")
                return result

        except httpx.HTTPStatusError as e:
            raise APIResponseError(
                f"{self.SERVICE_NAME} API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise APIConnectionError(
                f"Failed to connect to {self.SERVICE_NAME} API at {base_url}. "
                f"Is the {self.SERVICE_NAME} server running? Error: {str(e)}"
            ) from e
        except GreenroomError:
            raise
        except Exception as e:
            raise APIResponseError(f"{self.SERVICE_NAME} error: {str(e)}") from e
