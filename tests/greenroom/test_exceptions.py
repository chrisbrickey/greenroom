"""Tests for the custom exception hierarchy."""

import pytest

from greenroom.exceptions import (
    GreenroomError,
    APIConnectionError,
    APIResponseError,
    APITypeError,
    SamplingError,
)


@pytest.mark.parametrize("exc_class", [
    APIResponseError,
    APIConnectionError,
    APITypeError,
    SamplingError,
])
def test_custom_exceptions_inherit_from_greenroom_error(exc_class):
    """All custom exceptions should be subclasses of GreenroomError."""
    exc = exc_class("test message")
    assert isinstance(exc, GreenroomError)
    assert isinstance(exc, Exception)
    assert str(exc) == "test message"


def test_greenroom_error_is_base():
    """GreenroomError itself should be a direct Exception subclass."""
    assert issubclass(GreenroomError, Exception)
    exc = GreenroomError("base error")
    assert str(exc) == "base error"
