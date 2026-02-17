"""Tests for OllamaClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from greenroom.exceptions import APIConnectionError, APIResponseError, APITypeError
from greenroom.services.llm.ollama_client import OllamaClient


@pytest.mark.asyncio
@patch("greenroom.services.llm.ollama_client.httpx.AsyncClient")
async def test_generate_success(mock_async_client_class):
    """Test OllamaClient.generate() successfully calls Ollama API."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Ollama's response", "done": True}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    client = OllamaClient()
    result = await client.generate("Test prompt", "llama3.2:latest", 0.5, 200)

    assert result == {"response": "Ollama's response", "done": True}

    # Verify API call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "http://localhost:11434/api/generate" in call_args[0][0]
    assert call_args[1]["json"]["model"] == "llama3.2:latest"
    assert call_args[1]["json"]["prompt"] == "Test prompt"
    assert call_args[1]["json"]["stream"] is False
    assert call_args[1]["json"]["options"]["temperature"] == 0.5
    assert call_args[1]["json"]["options"]["num_predict"] == 200


@pytest.mark.asyncio
@patch("greenroom.services.llm.ollama_client.httpx.AsyncClient")
async def test_generate_handles_http_errors(mock_async_client_class):
    """Test OllamaClient.generate() handles HTTP status errors."""
    mock_client = MagicMock()
    mock_error_response = MagicMock()
    mock_error_response.status_code = 404
    mock_error_response.text = "Model not found"
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=mock_error_response)
    )
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    client = OllamaClient()
    with pytest.raises(APIResponseError, match="Ollama API error: 404 - Model not found"):
        await client.generate("Test", "unknown-model", 0.7, 100)


@pytest.mark.asyncio
@patch("greenroom.services.llm.ollama_client.httpx.AsyncClient")
async def test_generate_handles_connection_errors(mock_async_client_class):
    """Test OllamaClient.generate() handles connection errors."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    client = OllamaClient()
    with pytest.raises(APIConnectionError, match="Failed to connect to Ollama API"):
        await client.generate("Test", "llama3.2:latest", 0.7, 100)


@pytest.mark.asyncio
@patch("greenroom.services.llm.ollama_client.httpx.AsyncClient")
@patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://custom:8080"})
async def test_generate_uses_env_var(mock_async_client_class):
    """Test OllamaClient.generate() uses OLLAMA_BASE_URL from environment."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Response"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    client = OllamaClient()
    await client.generate("Test", "llama3.2:latest", 0.7, 100)

    # Verify custom URL was used
    call_args = mock_client.post.call_args
    assert "http://custom:8080/api/generate" in call_args[0][0]


@pytest.mark.asyncio
@patch("greenroom.services.llm.ollama_client.httpx.AsyncClient")
async def test_generate_raises_api_type_error_for_non_dict_response(mock_async_client_class):
    """Test OllamaClient.generate() raises APITypeError when response.json() is not a dict."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = ["not", "a", "dict"]
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    client = OllamaClient()
    with pytest.raises(APITypeError, match="Ollama API returned unexpected type"):
        await client.generate("Test", "llama3.2:latest", 0.7, 100)
