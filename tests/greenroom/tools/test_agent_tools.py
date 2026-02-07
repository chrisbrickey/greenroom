"""Tests for agent_tools.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from fastmcp import Context

from greenroom.services.llm import LLMService
from greenroom.tools.agent_tools import compare_llms


@pytest.mark.asyncio
async def test_compare_llms_validates_empty_prompt():
    """Test that empty prompt raises ValueError."""
    mock_service = MagicMock(spec=LLMService)
    mock_ctx = MagicMock(spec=Context)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await compare_llms(mock_service, mock_ctx, "")


@pytest.mark.asyncio
async def test_compare_llms_validates_whitespace_prompt():
    """Test that whitespace-only prompt raises ValueError."""
    mock_service = MagicMock(spec=LLMService)
    mock_ctx = MagicMock(spec=Context)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await compare_llms(mock_service, mock_ctx, "   ")


@pytest.mark.asyncio
async def test_compare_llms_validates_temperature():
    """Test that invalid temperature raises ValueError."""
    mock_service = MagicMock(spec=LLMService)
    mock_ctx = MagicMock(spec=Context)

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        await compare_llms(mock_service, mock_ctx, "Test", temperature=-0.1)

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        await compare_llms(mock_service, mock_ctx, "Test", temperature=2.1)


@pytest.mark.asyncio
async def test_compare_llms_validates_max_tokens():
    """Test that invalid max_tokens raises ValueError."""
    mock_service = MagicMock(spec=LLMService)
    mock_ctx = MagicMock(spec=Context)

    with pytest.raises(ValueError, match="Max tokens must be between 1 and 4000"):
        await compare_llms(mock_service, mock_ctx, "Test", max_tokens=0)

    with pytest.raises(ValueError, match="Max tokens must be between 1 and 4000"):
        await compare_llms(mock_service, mock_ctx, "Test", max_tokens=4001)


@pytest.mark.asyncio
async def test_compare_llms_accepts_boundary_temperature():
    """Test that boundary temperatures (0 and 2) are accepted."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(return_value="response")
    mock_service.generate_response_from_ollama = AsyncMock(return_value="response")

    result = await compare_llms(mock_service, mock_ctx, "Test", temperature=0)
    assert result["prompt"] == "Test"

    result = await compare_llms(mock_service, mock_ctx, "Test", temperature=2)
    assert result["prompt"] == "Test"


@pytest.mark.asyncio
async def test_compare_llms_accepts_boundary_max_tokens():
    """Test that boundary max_tokens (1 and 4000) are accepted."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(return_value="response")
    mock_service.generate_response_from_ollama = AsyncMock(return_value="response")

    result = await compare_llms(mock_service, mock_ctx, "Test", max_tokens=1)
    assert result["prompt"] == "Test"

    result = await compare_llms(mock_service, mock_ctx, "Test", max_tokens=4000)
    assert result["prompt"] == "Test"


@pytest.mark.asyncio
async def test_compare_llms_both_succeed():
    """Test that compare_llms correctly calls both LLMs and formats responses."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(
        return_value="Claude says: The sky is blue due to Rayleigh scattering."
    )
    mock_service.generate_response_from_ollama = AsyncMock(
        return_value="Ollama says: Light scattering causes the blue sky."
    )

    result = await compare_llms(
        mock_service,
        ctx=mock_ctx,
        prompt="Why is the sky blue?",
        temperature=0.7,
        max_tokens=100
    )

    # Verify structure
    assert "prompt" in result
    assert "responses" in result
    assert len(result["responses"]) == 2

    # Verify prompt
    assert result["prompt"] == "Why is the sky blue?"

    # Verify Claude response
    claude_resp = result["responses"][0]
    assert claude_resp["source"] == "claude resample"
    assert claude_resp["text"] == "Claude says: The sky is blue due to Rayleigh scattering."
    assert claude_resp["error"] is None
    assert claude_resp["length"] == len("Claude says: The sky is blue due to Rayleigh scattering.")

    # Verify alternative response
    alt_resp = result["responses"][1]
    assert alt_resp["source"] == "ollama alternative"
    assert alt_resp["text"] == "Ollama says: Light scattering causes the blue sky."
    assert alt_resp["error"] is None
    assert alt_resp["length"] == len("Ollama says: Light scattering causes the blue sky.")

    # Verify Claude was called via service with correct parameters
    mock_service.generate_response_from_claude.assert_called_once_with(
        mock_ctx, "Why is the sky blue?", 0.7, 100
    )

    # Verify Ollama was called via service with correct parameters
    mock_service.generate_response_from_ollama.assert_called_once_with(
        "Why is the sky blue?", 0.7, 100
    )


@pytest.mark.asyncio
async def test_compare_llms_uses_default_params():
    """Test that default temperature and max_tokens are used when not specified."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(return_value="Claude response")
    mock_service.generate_response_from_ollama = AsyncMock(return_value="Ollama response")

    # Call without specifying temperature or max_tokens
    result = await compare_llms(mock_service, mock_ctx, "Test prompt")

    # Verify service was called with default params
    mock_service.generate_response_from_claude.assert_called_once_with(
        mock_ctx, "Test prompt", 0.7, 500
    )
    mock_service.generate_response_from_ollama.assert_called_once_with(
        "Test prompt", 0.7, 500
    )


# --- Error handling ---


@pytest.mark.asyncio
async def test_compare_llms_claude_fails_ollama_succeeds():
    """Test graceful degradation when Claude fails but Ollama succeeds."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(
        side_effect=RuntimeError("Claude API error: Sample failed")
    )
    mock_service.generate_response_from_ollama = AsyncMock(return_value="Ollama response")

    result = await compare_llms(mock_service, mock_ctx, "Test prompt")

    # Verify Claude error is captured
    claude_resp = result["responses"][0]
    assert claude_resp["text"] is None
    assert claude_resp["error"] is not None
    assert "Claude API error" in claude_resp["error"]
    assert claude_resp["length"] == 0

    # Verify Ollama succeeded
    alt_resp = result["responses"][1]
    assert alt_resp["text"] == "Ollama response"
    assert alt_resp["error"] is None
    assert alt_resp["length"] == len("Ollama response")


@pytest.mark.asyncio
async def test_compare_llms_ollama_fails_claude_succeeds():
    """Test graceful degradation when Ollama fails but Claude succeeds."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(return_value="Claude response")
    mock_service.generate_response_from_ollama = AsyncMock(
        side_effect=RuntimeError("Ollama API error: 500 - Internal server error")
    )

    result = await compare_llms(mock_service, mock_ctx, "Test prompt")

    # Verify Claude succeeded
    claude_resp = result["responses"][0]
    assert claude_resp["text"] == "Claude response"
    assert claude_resp["error"] is None
    assert claude_resp["length"] == len("Claude response")

    # Verify Ollama error is captured
    alt_resp = result["responses"][1]
    assert alt_resp["text"] is None
    assert alt_resp["error"] is not None
    assert "Ollama API error" in alt_resp["error"]
    assert alt_resp["length"] == 0


@pytest.mark.asyncio
async def test_compare_llms_both_fail():
    """Test that both errors are captured when both LLMs fail with different exception types."""
    mock_ctx = MagicMock(spec=Context)

    mock_service = MagicMock(spec=LLMService)
    mock_service.generate_response_from_claude = AsyncMock(
        side_effect=ConnectionError("Claude connection failed")
    )
    mock_service.generate_response_from_ollama = AsyncMock(
        side_effect=ValueError("Ollama invalid value")
    )

    result = await compare_llms(mock_service, mock_ctx, "Test prompt")

    # Verify both errors are captured with their specific messages
    claude_resp = result["responses"][0]
    assert claude_resp["text"] is None
    assert claude_resp["error"] is not None
    assert "Claude connection failed" in claude_resp["error"]
    assert claude_resp["length"] == 0

    alt_resp = result["responses"][1]
    assert alt_resp["text"] is None
    assert alt_resp["error"] is not None
    assert "Ollama invalid value" in alt_resp["error"]
    assert alt_resp["length"] == 0
