"""Tests for tmon.serial_bus."""

import struct
from unittest.mock import MagicMock, patch

from tmon.serial_bus import SerialBus
from tmon.protocol import encode_frame, PROTO_CMD_POLL, PROTO_CMD_REPLY


class TestSerialBusSend:
    """Tests for SerialBus.send."""

    @patch("tmon.serial_bus.serial.Serial")
    def test_send_writes_data(self, mock_serial_cls):
        """send() writes data to the serial port."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        bus = SerialBus("/dev/ttyUSB0", 9600)
        data = b"\x01\x03\x01\x00\x80\x50"
        bus.send(data)
        mock_ser.write.assert_called_once_with(data)

    @patch("tmon.serial_bus.serial.Serial")
    def test_send_flushes_input_then_output(self, mock_serial_cls):
        """send() flushes input buffer before write, output after."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        bus = SerialBus("/dev/ttyUSB0", 9600)
        bus.send(b"\x01")
        calls = [c[0] for c in mock_ser.method_calls]
        assert "reset_input_buffer" in calls
        assert "flush" in calls
        # reset_input_buffer before write, flush after
        ri_idx = calls.index("reset_input_buffer")
        w_idx = calls.index("write")
        f_idx = calls.index("flush")
        assert ri_idx < w_idx < f_idx


class TestSerialBusReceive:
    """Tests for SerialBus.receive."""

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_assembles_frame(self, mock_serial_cls):
        """receive() reads header then payload+CRC."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser

        # Build a valid REPLY frame for slave 3
        payload = struct.pack("<Bhhhh", 0x03, 235, 198, 0x7FFF, 0x7FFF)
        frame = encode_frame(3, PROTO_CMD_REPLY, payload)

        # Simulate: first read returns header, second returns rest
        mock_ser.read = MagicMock(side_effect=[frame[:4], frame[4:]])

        bus = SerialBus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == frame

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_timeout_no_header(self, mock_serial_cls):
        """receive() returns b'' when no header bytes arrive."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"")

        bus = SerialBus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_timeout_partial_header(self, mock_serial_cls):
        """receive() returns b'' on partial header."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"\x01\x03")

        bus = SerialBus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_timeout_partial_payload(self, mock_serial_cls):
        """receive() returns b'' when payload is incomplete."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        # Header says LEN=9, but only 3 bytes of tail arrive
        header = b"\x01\x03\x02\x09"
        mock_ser.read = MagicMock(side_effect=[header, b"\x03\xEB\x00"])

        bus = SerialBus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == b""

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_sets_timeout_from_constant(self, mock_serial_cls):
        """receive() sets serial timeout from TIMEOUT_MS constant."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.read = MagicMock(return_value=b"")

        bus = SerialBus("/dev/ttyUSB0", 9600)
        bus.receive()
        assert mock_ser.timeout == 200 / 1000.0

    @patch("tmon.serial_bus.serial.Serial")
    def test_receive_poll_frame(self, mock_serial_cls):
        """receive() handles a zero-payload POLL frame."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser

        frame = encode_frame(3, PROTO_CMD_POLL, b"")
        mock_ser.read = MagicMock(side_effect=[frame[:4], frame[4:]])

        bus = SerialBus("/dev/ttyUSB0", 9600)
        result = bus.receive()
        assert result == frame


class TestSerialBusContextManager:
    """Tests for SerialBus context manager protocol."""

    @patch("tmon.serial_bus.serial.Serial")
    def test_with_block_closes_port(self, mock_serial_cls):
        """Exiting a with block closes the serial port."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        with SerialBus("/dev/ttyUSB0", 9600) as bus:
            bus.send(b"\x01")
        mock_ser.close.assert_called_once()

    @patch("tmon.serial_bus.serial.Serial")
    def test_enter_returns_self(self, mock_serial_cls):
        """__enter__ returns the SerialBus instance."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        bus = SerialBus("/dev/ttyUSB0", 9600)
        assert bus.__enter__() is bus
        bus.close()
