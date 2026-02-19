"""Agent comparison tools for the greenroom MCP server."""

import asyncio

from greenroom.models.responses import LLMComparisonResultDict, LLMResponseEntryDict

from fastmcp import FastMCP, Context

from greenroom.services.llm import LLMService


def register_agent_tools(mcp: FastMCP) -> None:
    """Register agent comparison tools with the MCP server."""

    service = LLMService()

    @mcp.tool()
    async def compare_llm_responses(
        ctx: Context,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> LLMComparisonResultDict:
        """
        Compare how multiple agents respond to the same prompt.

        As of 2026, this defaults to comparing a resampling of claude
        with a freshly generated response from Ollama.

        Args:
            prompt: The prompt to send to both LLMs
            temperature: Temperature for both LLMs (default: 0.7)
            max_tokens: Maximum tokens for responses (default: 500)

        Returns:
            Dictionary containing:
            {
                "prompt": "original prompt text",
                "responses": [
                    {
                        "source": "claude resample",
                        "text": "Resampled response...",
                        "error": None,
                        "length": 150
                    },
                    {
                        "source": "ollama alternative",
                        "text": "Alternative response...",
                        "error": None,
                        "length": 142
                    }
                ]
            }

        Raises:
            ValueError: If prompt is empty or invalid parameters provided
        """

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await compare_llms(service, ctx, prompt, temperature, max_tokens)


async def compare_llms(
    llm_service: LLMService,
    ctx: Context,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> LLMComparisonResultDict:

    # Validate inputs
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if temperature < 0 or temperature > 2:
        raise ValueError("Temperature must be between 0 and 2")

    if max_tokens < 1 or max_tokens > 4000:
        raise ValueError("Max tokens must be between 1 and 4000")

    # Call multiple LLMs in parallel
    resampled_result, alternative_result = await asyncio.gather(
        llm_service.resample_current_llm(ctx, prompt, temperature, max_tokens),
        llm_service.generate_response_from_alternative_llm(prompt, temperature, max_tokens),
        return_exceptions=True
    )

    combined_responses = [("claude resample", resampled_result), ("ollama alternative", alternative_result)]
    return _format_responses(prompt, combined_responses)


def _format_responses(
    prompt: str,
    labeled_responses: list[tuple[str, str | BaseException]]
) -> LLMComparisonResultDict:
    """Format labeled LLM responses into a structured comparison result."""

    combined_response: LLMComparisonResultDict = { "prompt": prompt, "responses": [] }

    for label, response in labeled_responses:
        if isinstance(response, BaseException):
            entry: LLMResponseEntryDict = {"source": label, "text": None, "error": str(response), "length": 0}
        else:
            entry = {"source": label, "text": response, "error": None, "length": len(response)}

        combined_response["responses"].append(entry)

    return combined_response
