"""WiFi bus abstraction for TCP-based communication.

Master runs a TCP server; each ESP32 slave connects as a client.
Slaves identify themselves by sending their 1-byte address on connect.
The same binary protocol frames travel over TCP instead of serial.

Example:
    >>> from tmon.wifi_bus import WifiBus
    >>> bus = WifiBus("0.0.0.0", 5555, timeout_ms=200)
    >>> # Slaves connect in background...
    >>> bus.send(poll_frame)   # Routes to slave based on ADDR byte
    >>> response = bus.receive()
"""

import socket
import threading


class WifiBus:
    """TCP server for WiFi slave connections.

    Speaks the same binary protocol as RS-485, but over TCP sockets.
    Each slave connects and sends its 1-byte address as identification.
    The server maps addresses to sockets for routing.

    Args:
        host: Interface to bind (e.g. ``"0.0.0.0"`` for all).
        port: TCP port to listen on (e.g. ``5555``).
        timeout_ms: Receive timeout in milliseconds.

    Example:
        >>> bus = WifiBus("0.0.0.0", 5555, timeout_ms=200)
        >>> bus.send(b"\\x01\\x03\\x01\\x00...")  # Sends to slave 3
        >>> reply = bus.receive()
        >>> bus.close()
    """

    _HEADER_LEN = 4
    _CRC_LEN = 2

    def __init__(self, host: str, port: int, timeout_ms: int):
        """Start the TCP server and accept thread."""
        self._timeout_ms = timeout_ms
        self._sockets: dict[int, socket.socket] = {}
        self._lock = threading.Lock()
        self._current_addr: int | None = None

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((host, port))
        self._server.listen(8)
        self._server.settimeout(0.1)

        self._running = True
        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True
        )
        self._accept_thread.start()

    def _accept_loop(self) -> None:
        """Background thread: accept connections, read address byte."""
        while self._running:
            try:
                conn, _ = self._server.accept()
                conn.settimeout(5.0)
                try:
                    addr_byte = conn.recv(1)
                    if len(addr_byte) == 1:
                        slave_addr = addr_byte[0]
                        with self._lock:
                            old = self._sockets.get(slave_addr)
                            if old is not None:
                                try:
                                    old.close()
                                except OSError:
                                    pass
                            self._sockets[slave_addr] = conn
                    else:
                        conn.close()
                except OSError:
                    conn.close()
            except socket.timeout:
                pass
            except OSError:
                if self._running:
                    pass

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes, or b'' on timeout/error."""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return b""
            data += chunk
        return data

    def send(self, data: bytes) -> None:
        """Send frame to the slave identified by the ADDR byte in the frame."""
        if len(data) < 2:
            return
        addr = data[1]
        self._current_addr = addr

        with self._lock:
            sock = self._sockets.get(addr)

        if sock is None:
            return

        try:
            sock.sendall(data)
        except OSError:
            with self._lock:
                if self._sockets.get(addr) is sock:
                    del self._sockets[addr]

    def receive(self) -> bytes:
        """Receive a complete protocol frame from the current slave."""
        if self._current_addr is None:
            return b""

        with self._lock:
            sock = self._sockets.get(self._current_addr)

        if sock is None:
            return b""

        try:
            sock.settimeout(self._timeout_ms / 1000.0)
            header = self._recv_exact(sock, self._HEADER_LEN)
            if len(header) < self._HEADER_LEN:
                return b""

            payload_len = header[3]
            remaining = payload_len + self._CRC_LEN
            tail = self._recv_exact(sock, remaining)
            if len(tail) < remaining:
                return b""

            return header + tail
        except socket.timeout:
            return b""
        except OSError:
            with self._lock:
                if self._sockets.get(self._current_addr) is sock:
                    del self._sockets[self._current_addr]
            return b""

    def close(self) -> None:
        """Shut down the server and all connections."""
        self._running = False
        self._accept_thread.join(timeout=1.0)

        with self._lock:
            for sock in self._sockets.values():
                try:
                    sock.close()
                except OSError:
                    pass
            self._sockets.clear()

        try:
            self._server.close()
        except OSError:
            pass
