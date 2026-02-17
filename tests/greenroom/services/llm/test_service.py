"""Tests for LLMService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from greenroom.services.llm.service import LLMService


@pytest.mark.asyncio
async def test_generate_response_from_claude_success():
    """Test LLMService.generate_response_from_claude() successfully calls ctx.sample."""
    mock_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Claude's response"
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    service = LLMService()
    result = await service.resample_current_llm(mock_ctx, "Test prompt", 0.5, 200)

    assert result == "Claude's response"
    mock_ctx.sample.assert_called_once_with(
        messages="Test prompt",
        temperature=0.5,
        max_tokens=200
    )


@pytest.mark.asyncio
async def test_generate_response_from_claude_handles_errors():
    """Test LLMService.generate_response_from_claude() wraps errors in RuntimeError."""
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=Exception("Sample failed"))

    service = LLMService()
    with pytest.raises(RuntimeError, match="Claude API error: Sample failed"):
        await service.resample_current_llm(mock_ctx, "Test", 0.7, 100)


@pytest.mark.asyncio
async def test_generate_response_from_ollama_success():
    """Test LLMService.generate_response_from_ollama() delegates to client and extracts response."""
    service = LLMService()
    service.client.generate = AsyncMock(
        return_value={"response": "Ollama's response", "done": True}
    )

    result = await service.generate_response_from_alternative_llm("Test prompt", 0.5, 200)

    assert result == "Ollama's response"
    service.client.generate.assert_called_once_with(
        "Test prompt", "llama3.2:latest", 0.5, 200
    )


@pytest.mark.asyncio
async def test_generate_response_from_ollama_empty_response():
    """Test LLMService.generate_response_from_ollama() returns empty string when response key missing."""
    service = LLMService()
    service.client.generate = AsyncMock(return_value={"done": True})

    result = await service.generate_response_from_alternative_llm("Test", 0.7, 100)

    assert result == ""


@pytest.mark.asyncio
async def test_generate_response_from_ollama_propagates_runtime_error():
    """Test LLMService.generate_response_from_ollama() propagates RuntimeError from client."""
    service = LLMService()
    service.client.generate = AsyncMock(
        side_effect=RuntimeError("Ollama API error: 500 - Internal error")
    )

    with pytest.raises(RuntimeError, match="Ollama API error"):
        await service.generate_response_from_alternative_llm("Test", 0.7, 100)


@pytest.mark.asyncio
async def test_generate_response_from_ollama_propagates_connection_error():
    """Test LLMService.generate_response_from_ollama() propagates ConnectionError from client."""
    service = LLMService()
    service.client.generate = AsyncMock(
        side_effect=ConnectionError("Failed to connect to Ollama API")
    )

    with pytest.raises(ConnectionError, match="Failed to connect to Ollama API"):
        await service.generate_response_from_alternative_llm("Test", 0.7, 100)
