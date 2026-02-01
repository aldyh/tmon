"""Shared pytest fixtures for tmon tests."""


class FakeBus:
    """Test double for Bus.

    Pre-loaded with canned responses; records all sent data.
    Responses are returned in FIFO order.  When the response
    queue is empty, receive() returns ``b""``.

    Args:
        responses: List of bytes objects to return from receive().

    Example:
        >>> bus = FakeBus([b"\\x01..."])
        >>> bus.send(b"poll frame")
        >>> bus.receive(200)
        b'\\x01...'
        >>> bus.sent
        [b'poll frame']
    """

    def __init__(self, responses):
        """Initialize with canned responses.

        Args:
            responses: List of bytes to return from successive
                receive() calls.
        """
        self._responses = list(responses)
        self.sent = []

    def send(self, data):
        """Record *data* for later inspection.

        Args:
            data: Bytes that would be transmitted on a real bus.
        """
        self.sent.append(data)

    def receive(self, timeout_ms):
        """Return the next canned response, or ``b""`` if exhausted.

        Args:
            timeout_ms: Ignored (present for API compatibility).

        Returns:
            bytes: Next canned response or ``b""``.
        """
        if self._responses:
            return self._responses.pop(0)
        return b""
