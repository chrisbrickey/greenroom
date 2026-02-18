"""Service layer for LLM interactions."""

from fastmcp import Context

from greenroom.exceptions import GreenroomError, SamplingError
from greenroom.services.llm.ollama_client import OllamaClient
from greenroom.services.llm.config import OLLAMA_DEFAULT_MODEL
from greenroom.services.protocols import LLMClient


class LLMService:
    """Service that encapsulates LLM calling logic.

    Provides methods for calling Claude (via MCP sampling) and Ollama,
    handling response extraction and error wrapping.
    """

    SAMPLING_SOURCE = "Claude"

    def __init__(self, client: LLMClient | None = None):
        """Initialize the LLM service."""
        self.client: LLMClient = client or OllamaClient()

    async def resample_current_llm(
        self,
        ctx: Context,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Resample the current client's LLM using the ctx.sample()
        abstraction provided by the FastMCP framework.

        Args:
            ctx: FastMCP context for LLM sampling
            prompt: The prompt to send
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            response text

        Raises:
            SamplingError: Any error from ctx.sample()
        """
        try:
            response = await ctx.sample(
                messages=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            if not hasattr(response, "text"):
                raise SamplingError(f"{self.SAMPLING_SOURCE} API returned unexpected content type: {type(response)}")
            return response.text
        except GreenroomError:
            raise
        except Exception as e:
            raise SamplingError(f"{self.SAMPLING_SOURCE} API error: {str(e)}") from e

    async def generate_response_from_alternative_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call a different LLM client.

        As of 2026, this defaults to Ollama so
        it delegates to OllamaClient.generate()
        and extracts the response text.

        Args:
            prompt: The prompt to send
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            response text

        Raises:
            APIResponseError: If API returns an error
            APIConnectionError: If unable to connect to API
        """

        data = await self.client.generate(prompt, OLLAMA_DEFAULT_MODEL, temperature, max_tokens)

        # data is a Dict whose values can be Any. Assigning to str before calling data.get() makes the type explicit.
        result: str = data.get("response", "")
        return result
