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

    def __init__(self):
        """Initialize the LLM service."""
        self.client: LLMClient = OllamaClient()

    async def generate_response_from_claude(
        self,
        ctx: Context,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Claude using the ctx.sample() abstraction 
        provided by the FastMCP framework, which is why
        a Claude-specific client is unnecessary.

        Args:
            ctx: FastMCP context for LLM sampling
            prompt: The prompt to send
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            Claude's response text

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

    async def generate_response_from_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Ollama via the client.

        Delegates to OllamaClient.generate() and extracts the response text
        from the raw API response dictionary.

        Args:
            prompt: The prompt to send
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate

        Returns:
            Ollama's response text

        Raises:
            APIResponseError: If Ollama API returns an error
            APIConnectionError: If unable to connect to Ollama API
        """

        data = await self.client.generate(prompt, OLLAMA_DEFAULT_MODEL, temperature, max_tokens)

        # data is a Dict whose values can be Any. Assigning to str before calling data.get() makes the type explicit.
        result: str = data.get("response", "")
        return result
