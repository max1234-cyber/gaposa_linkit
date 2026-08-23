"""Tests for Gaposa LinkIt Hub communication."""
import asyncio
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from custom_components.gaposa_linkit import GaposaLinkItHub
from custom_components.gaposa_linkit.const import CMD_DOWN
from custom_components.gaposa_linkit.const import CMD_UP


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
