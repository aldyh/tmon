"""Tests for tmon.bus."""

from unittest.mock import MagicMock, patch

from tmon.bus import Bus
from tmon.config import BUS_TIMEOUT_MS
from tmon.protocol import encode_request, PROTO_CMD_POLL, PROTO_CMD_REPLY

import struct


class TestBusSend:
    """Tests for Bus.send."""

    @patch("tmon.bus.serial.Serial")
    def test_send_writes_data(self, mock_serial_cls):
        """send() writes data to the serial port."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        bus = Bus("/dev/ttyUSB0", 9600)
        data = b"\x01\x03\x01\x00\x80\x50"
        bus.send(data)
        mock_ser.write.assert_called_once_with(data)

    @patch("tmon.bus.serial.Serial")
    def test_send_flushes_input_then_output(self, mock_serial_cls):
        """send() flushes input buffer before write, output after."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        bus = Bus("/dev/ttyUSB0", 9600)
        bus.send(b"\x01")
        calls = [c[0] for c in mock_ser.method_calls]
        assert "reset_input_buffer" in calls
        assert "flush" in calls
        # reset_input_buffer before write, flush after
        ri_idx = calls.index("reset_input_buffer")
        w_idx = calls.index("write")
        f_idx = calls.index("flush")
        assert ri_idx < w_idx < f_idx


class TestBusReceive:
    """Tests for Bus.receive."""

    @patch("tmon.bus.serial.Serial")
    def test_receive_assembles_frame(self, mock_serial_cls):
        """receive() reads header then payload+CRC."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser

        # Build a valid REPLY frame for slave 3
        payload = struct.pack("<Bhhhh", 0x03, 235, 198, 0x7FFF, 0x7FFF)
        frame = encode_request(3, PROTO_CMD_REPLY, payload)

        # Simulate: first read returns header, second returns rest
        mock_ser.read = MagicMock(side_effect=[frame[:4], frame[4:]])

        bus = Bus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == frame

    @patch("tmon.bus.serial.Serial")
    def test_receive_timeout_no_header(self, mock_serial_cls):
        """receive() returns b'' when no header bytes arrive."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"")

        bus = Bus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.bus.serial.Serial")
    def test_receive_timeout_partial_header(self, mock_serial_cls):
        """receive() returns b'' on partial header."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"\x01\x03")

        bus = Bus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.bus.serial.Serial")
    def test_receive_timeout_partial_payload(self, mock_serial_cls):
        """receive() returns b'' when payload is incomplete."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        # Header says LEN=9, but only 3 bytes of tail arrive
        header = b"\x01\x03\x02\x09"
        mock_ser.read = MagicMock(side_effect=[header, b"\x03\xEB\x00"])

        bus = Bus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.bus.serial.Serial")
    def test_receive_sets_timeout_from_config(self, mock_serial_cls):
        """receive() sets serial timeout from BUS_TIMEOUT_MS config."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"")

        bus = Bus("/dev/ttyUSB0", 9600)
        bus.receive()
        assert mock_ser.timeout == BUS_TIMEOUT_MS / 1000.0

    @patch("tmon.bus.serial.Serial")
    def test_receive_poll_frame(self, mock_serial_cls):
        """receive() handles a zero-payload POLL frame."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser

        frame = encode_request(3, PROTO_CMD_POLL, b"")
        mock_ser.read = MagicMock(side_effect=[frame[:4], frame[4:]])

        bus = Bus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == frame
