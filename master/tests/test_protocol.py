"""Tests for tmon.protocol."""

from tmon import protocol


def test_placeholder():
    """Verify the protocol module is importable."""
    assert hasattr(protocol, "encode_request")
    assert hasattr(protocol, "decode_frame")
