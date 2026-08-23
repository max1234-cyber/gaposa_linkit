import asyncio
import logging
from abc import ABC
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_CHANNELS
from .const import CONF_CONNECTION_TYPE
from .const import CONF_SERIAL_PORT
from .const import CONNECTION_TYPE_USB
from .const import DEFAULT_BAUD_RATE
from .const import DEFAULT_PORT
from .const import DOMAIN
from .const import get_config_update_signal

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["cover", "number", "switch"]
HUB_REPLY_SIZE = 3


def create_hub(data: Mapping[str, Any]) -> "GaposaLinkItHub":
    """Factory: return the correct hub implementation based on connection type."""
    if data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_USB:
        return GaposaLinkItUSBHub(
            serial_port=data[CONF_SERIAL_PORT],
            baud_rate=DEFAULT_BAUD_RATE,
        )
    return GaposaLinkItIPHub(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    hub = create_hub(entry.data)
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "entry_data": dict(entry.data),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the update listener for the Options Flow (Configure button)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _connection_changed(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    """Return True if any connection-relevant field has changed."""
    for key in (CONF_CONNECTION_TYPE, CONF_HOST, CONF_SERIAL_PORT):
        if previous.get(key) != current.get(key):
            return True
    if previous.get(CONF_PORT, DEFAULT_PORT) != current.get(CONF_PORT, DEFAULT_PORT):
        return True
    if set(previous.get(CONF_CHANNELS, [])) != set(current.get(CONF_CHANNELS, [])):
        return True
    return False


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update when the user changes settings via the UI."""
    runtime_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    previous_data = runtime_data.get("entry_data", {}) if runtime_data else {}

    if _connection_changed(previous_data, entry.data):
        await hass.config_entries.async_reload(entry.entry_id)
        return

    if runtime_data is not None:
        runtime_data["entry_data"] = dict(entry.data)

    async_dispatcher_send(hass, get_config_update_signal(entry.entry_id), entry.data)


# ---------------------------------------------------------------------------
# Hub base class
# ---------------------------------------------------------------------------


class GaposaLinkItHub(ABC):
    """Abstract base class for LinkIt hub communication."""

    def _build_payload(self, bank: int, channel: int, command: int) -> bytes:
        b0 = 0x67
        b1 = bank
        b2 = channel
        b3 = command
        b4 = b0 ^ b1 ^ b2 ^ b3  # XOR checksum
        return bytes([b0, b1, b2, b3, b4])

    @abstractmethod
    async def send_command(self, bank: int, channel: int, command: int) -> str | None:
        """Send a command to the hub and return the reply (if any)."""

    async def _read_available_bytes(
        self, reader: asyncio.StreamReader, *, max_reads: int = 5
    ) -> bytes:
        """Read immediately available bytes without blocking for long."""
        chunks: list[bytes] = []
        total_read = 0
        for _ in range(max_reads):
            remaining = HUB_REPLY_SIZE - total_read
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(reader.read(remaining), timeout=0.01)
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            total_read += len(chunk)
        return b"".join(chunks)

    async def _read_reply(self, reader: asyncio.StreamReader, *, source: str) -> str | None:
        """Read the reply and log partial bytes when the initial read times out."""
        try:
            data = await asyncio.wait_for(reader.readexactly(HUB_REPLY_SIZE), timeout=3.0)
        except asyncio.TimeoutError:
            partial_data = await self._read_available_bytes(reader)
            if partial_data:
                partial_reply = partial_data.decode("utf-8", errors="ignore").strip()
                _LOGGER.warning(
                    "Timed out waiting for reply from %s; partial reply (%s bytes): hex=%s, decoded=%r",
                    source,
                    len(partial_data),
                    partial_data.hex(),
                    partial_reply,
                )
                return partial_reply
            _LOGGER.warning("Timed out waiting for reply from %s (no response within 3s).", source)
            return None
        except asyncio.IncompleteReadError as err:
            if err.partial:
                partial_reply = err.partial.decode("utf-8", errors="ignore").strip()
                _LOGGER.warning(
                    "%s closed the connection with a partial reply (%s/%s bytes): hex=%s, decoded=%r",
                    source,
                    len(err.partial),
                    HUB_REPLY_SIZE,
                    err.partial.hex(),
                    partial_reply,
                )
                return partial_reply
            _LOGGER.warning("%s closed the connection without returning a reply.", source)
            return None

        reply_str = data.decode("utf-8", errors="ignore").strip()
        _LOGGER.info("Received reply from Gaposa hub: %s", reply_str)
        return reply_str


# ---------------------------------------------------------------------------
# IP (TCP) hub implementation
# ---------------------------------------------------------------------------


class GaposaLinkItIPHub(GaposaLinkItHub):
    """Communicate with the LinkIt Hub via an IP-to-Serial adapter (e.g. iTach IP2SL)."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._lock = asyncio.Lock()

    async def send_command(self, bank: int, channel: int, command: int) -> str | None:
        """Sends a raw 5-byte command payload over TCP to the iTach converter asynchronously."""
        payload = self._build_payload(bank, channel, command)

        reply_str = None
        async with self._lock:
            try:
                # Open non-blocking TCP socket connection (with a 5-second connection timeout)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=5.0,
                )

                # Send the raw bytes down the wire
                writer.write(payload)
                await writer.drain()
                _LOGGER.info("Sent Gaposa command: [%s] to %s:%s", payload.hex(), self.host, self.port)

                try:
                    # Wait for and read the response back from the LinkIt hub.
                    reply_str = await self._read_reply(reader, source=f"{self.host}:{self.port}")
                finally:
                    # Cleanly close the socket after the read attempt finishes or times out
                    writer.close()
                    await writer.wait_closed()

            except asyncio.TimeoutError:
                _LOGGER.error("Timeout: Could not connect to iTach at %s:%s within 5 seconds.", self.host, self.port)
            except Exception as err:
                _LOGGER.error("Error communicating with iTach at %s:%s - %s", self.host, self.port, err)

        return reply_str


# ---------------------------------------------------------------------------
# USB (serial) hub implementation
# ---------------------------------------------------------------------------


class GaposaLinkItUSBHub(GaposaLinkItHub):
    """Communicate with the LinkIt Hub via a directly attached USB-to-Serial adapter."""

    def __init__(self, serial_port: str, baud_rate: int = DEFAULT_BAUD_RATE):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self._lock = asyncio.Lock()

    async def send_command(self, bank: int, channel: int, command: int) -> str | None:
        """Sends a raw 5-byte command payload over a USB serial port."""
        import serial_asyncio  # type: ignore[import-untyped]  # noqa: PLC0415  (lazy import – optional dependency)

        payload = self._build_payload(bank, channel, command)

        reply_str = None
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    serial_asyncio.open_serial_connection(
                        url=self.serial_port,
                        baudrate=self.baud_rate,
                        bytesize=8,
                        parity="N",
                        stopbits=1,
                    ),
                    timeout=5.0,
                )

                writer.write(payload)
                await writer.drain()
                _LOGGER.info(
                    "Sent Gaposa command: [%s] to USB serial %s",
                    payload.hex(),
                    self.serial_port,
                )

                try:
                    reply_str = await self._read_reply(reader, source=f"USB serial {self.serial_port}")
                finally:
                    writer.close()

            except asyncio.TimeoutError:
                _LOGGER.error("Timeout: Could not open USB serial port %s within 5 seconds.", self.serial_port)
            except Exception as err:
                _LOGGER.error("Error communicating via USB serial port %s - %s", self.serial_port, err)

        return reply_str


# Backward-compatible alias so existing tests importing GaposaLinkItHub still work.
GaposaLinkItHub = GaposaLinkItIPHub
