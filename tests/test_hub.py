"""Tests for Gaposa LinkIt Hub communication."""
import asyncio
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT

from custom_components.gaposa_linkit import GaposaLinkItHub
from custom_components.gaposa_linkit import GaposaLinkItIPHub
from custom_components.gaposa_linkit import GaposaLinkItUSBHub
from custom_components.gaposa_linkit import HUB_REPLY_SIZE
from custom_components.gaposa_linkit import create_hub
from custom_components.gaposa_linkit.const import CMD_DOWN
from custom_components.gaposa_linkit.const import CMD_UP
from custom_components.gaposa_linkit.const import CONF_CONNECTION_TYPE
from custom_components.gaposa_linkit.const import CONF_SERIAL_PORT
from custom_components.gaposa_linkit.const import CONNECTION_TYPE_IP
from custom_components.gaposa_linkit.const import CONNECTION_TYPE_USB
from custom_components.gaposa_linkit.const import DEFAULT_BAUD_RATE

# ---------------------------------------------------------------------------
# IP hub (existing)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hub_initialization():
    """Test hub initialization."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)
    assert hub.host == "192.168.1.100"
    assert hub.port == 4999
    assert hub._lock is not None


@pytest.mark.asyncio
async def test_hub_send_command_success():
    """Test successful command send."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"OK")

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result == "OK"
        mock_writer.write.assert_called_once()
        mock_writer.close.assert_called_once()
        mock_reader.read.assert_called_once_with(HUB_REPLY_SIZE)


@pytest.mark.asyncio
async def test_hub_send_command_checksum():
    """Test command checksum calculation."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"OK")

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        await hub.send_command(0x00, 0x01, 0xdd)

        # Verify the payload was sent
        call_args = mock_writer.write.call_args
        payload = call_args[0][0]

        # Payload should be: b0=0x67, b1=0x00, b2=0x01, b3=0xdd, b4=checksum
        assert payload[0] == 0x67
        assert payload[1] == 0x00
        assert payload[2] == 0x01
        assert payload[3] == 0xdd
        # Checksum is XOR of all bytes
        expected_checksum = 0x67 ^ 0x00 ^ 0x01 ^ 0xdd
        assert payload[4] == expected_checksum


@pytest.mark.asyncio
async def test_hub_send_command_timeout_connection():
    """Test connection timeout."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    with patch("asyncio.open_connection", side_effect=asyncio.TimeoutError()):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result is None


@pytest.mark.asyncio
async def test_hub_send_command_timeout_read():
    """Test read timeout."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result is None
        mock_writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_hub_send_command_connection_error():
    """Test connection error."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    with patch("asyncio.open_connection", side_effect=OSError("Connection refused")):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result is None


@pytest.mark.asyncio
async def test_hub_send_command_empty_response():
    """Test empty response from hub."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"")

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result is None


@pytest.mark.asyncio
async def test_hub_send_command_unicode_response():
    """Test response with unicode content."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"Response: OK")

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result == "Response: OK"


@pytest.mark.asyncio
async def test_hub_concurrent_commands():
    """Test that commands are serialized via lock."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"OK")

    call_count = 0

    async def mock_open(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # Simulate network delay
        return (mock_reader, mock_writer)

    with patch("asyncio.open_connection", side_effect=mock_open):
        # Send two commands concurrently
        results = await asyncio.gather(
            hub.send_command(0, 1, CMD_UP),
            hub.send_command(0, 2, CMD_DOWN),
        )

        assert len(results) == 2
        assert all(r == "OK" for r in results)


# ---------------------------------------------------------------------------
# USB hub
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usb_hub_initialization():
    """Test USB hub uses the fixed baud rate required by the LinkIt Hub."""
    hub = GaposaLinkItUSBHub("/dev/ttyUSB0")
    assert hub.serial_port == "/dev/ttyUSB0"
    assert hub.baud_rate == DEFAULT_BAUD_RATE
    assert hub._lock is not None


@pytest.mark.asyncio
async def test_usb_hub_send_command_success():
    """Test successful command send via USB."""
    hub = GaposaLinkItUSBHub("/dev/ttyUSB0")

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"OK")

    mock_serial_asyncio = AsyncMock()
    mock_serial_asyncio.open_serial_connection = AsyncMock(
        return_value=(mock_reader, mock_writer)
    )

    import sys
    sys.modules["serial_asyncio"] = mock_serial_asyncio

    try:
        result = await hub.send_command(0, 1, CMD_UP)
        assert result == "OK"
        mock_writer.write.assert_called_once()
        mock_writer.close.assert_called_once()
        mock_reader.read.assert_called_once_with(HUB_REPLY_SIZE)
        mock_serial_asyncio.open_serial_connection.assert_called_once_with(
            url="/dev/ttyUSB0",
            baudrate=DEFAULT_BAUD_RATE,
            bytesize=8,
            parity="N",
            stopbits=1,
        )
    finally:
        del sys.modules["serial_asyncio"]


@pytest.mark.asyncio
async def test_hub_send_command_timeout_logs_partial_reply(caplog):
    """When timeout happens, any late partial bytes are logged and returned."""
    hub = GaposaLinkItHub("192.168.1.100", 4999)

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(side_effect=[asyncio.TimeoutError(), b"#6", asyncio.TimeoutError()])

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        result = await hub.send_command(0, 1, CMD_UP)
        assert result == "#6"
        assert "partial reply" in caplog.text
        assert mock_reader.read.await_args_list[0].args == (HUB_REPLY_SIZE,)


@pytest.mark.asyncio
async def test_usb_hub_send_command_checksum():
    """Test USB hub command checksum calculation."""
    hub = GaposaLinkItUSBHub("/dev/ttyUSB0")

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_reader.read = AsyncMock(return_value=b"OK")

    mock_serial_asyncio = AsyncMock()
    mock_serial_asyncio.open_serial_connection = AsyncMock(
        return_value=(mock_reader, mock_writer)
    )

    import sys
    sys.modules["serial_asyncio"] = mock_serial_asyncio

    try:
        await hub.send_command(0x00, 0x01, 0xdd)
        call_args = mock_writer.write.call_args
        payload = call_args[0][0]
        assert payload[0] == 0x67
        assert payload[1] == 0x00
        assert payload[2] == 0x01
        assert payload[3] == 0xdd
        expected_checksum = 0x67 ^ 0x00 ^ 0x01 ^ 0xdd
        assert payload[4] == expected_checksum
    finally:
        del sys.modules["serial_asyncio"]


@pytest.mark.asyncio
async def test_usb_hub_send_command_error():
    """Test USB hub handles serial port errors gracefully."""
    hub = GaposaLinkItUSBHub("/dev/ttyUSB0")

    mock_serial_asyncio = AsyncMock()
    mock_serial_asyncio.open_serial_connection = AsyncMock(
        side_effect=OSError("No such file or directory")
    )

    import sys
    sys.modules["serial_asyncio"] = mock_serial_asyncio

    try:
        result = await hub.send_command(0, 1, CMD_UP)
        assert result is None
    finally:
        del sys.modules["serial_asyncio"]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_create_hub_ip():
    """create_hub returns a GaposaLinkItIPHub for IP config."""
    hub = create_hub(
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 4999,
        }
    )
    assert isinstance(hub, GaposaLinkItIPHub)
    assert hub.host == "192.168.1.100"
    assert hub.port == 4999


def test_create_hub_usb():
    """create_hub returns a GaposaLinkItUSBHub with the fixed baud rate."""
    hub = create_hub(
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
        }
    )
    assert isinstance(hub, GaposaLinkItUSBHub)
    assert hub.serial_port == "/dev/ttyUSB0"
    assert hub.baud_rate == DEFAULT_BAUD_RATE


def test_create_hub_defaults_to_ip():
    """create_hub defaults to IP when connection type is absent."""
    hub = create_hub({CONF_HOST: "192.168.1.100"})
    assert isinstance(hub, GaposaLinkItIPHub)
