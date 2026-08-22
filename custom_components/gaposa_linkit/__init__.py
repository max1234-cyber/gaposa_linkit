import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    # Safely get host and port from config entry data
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 4999)

    hub = GaposaLinkItHub(host, port)
    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])
    
    # Register the update listener for the Options Flow (Configure button)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["cover"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update when the user changes settings via the UI."""
    await hass.config_entries.async_reload(entry.entry_id)

class GaposaLinkItHub:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._lock = asyncio.Lock()

    async def send_command(self, bank: int, channel: int, command: int):
        """Sends a raw 5-byte command payload over TCP to the iTach converter asynchronously."""
        b0 = 0x67
        b1 = bank
        b2 = channel
        b3 = command
        b4 = b0 ^ b1 ^ b2 ^ b3  # XOR checksum
        payload = bytes([b0, b1, b2, b3, b4])

        reply_str = None
        async with self._lock:
            try:
                # Open non-blocking TCP socket connection (with a 5-second connection timeout)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), 
                    timeout=5.0
                )
        
                # Send the raw bytes down the wire
                writer.write(payload)
                await writer.drain()
                _LOGGER.info("Sent Gaposa command: [%s] to %s:%s", payload.hex(), self.host, self.port)
        
                # Wait for and read the response back from the LinkIt hub (3-second timeout)
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=3.0)
                    if data:
                        reply_str = data.decode('utf-8', errors='ignore').strip()
                        _LOGGER.info("Received reply from Gaposa hub: %s", reply_str)
                    else:
                        _LOGGER.warning("iTach/LinkIt closed the connection without returning a reply.")
                except asyncio.TimeoutError:
                    _LOGGER.warning("Timed out waiting for reply from Gaposa hub (no response within 3s).")
                finally:
                    # Cleanly close the socket after the read attempt finishes or times out
                    writer.close()
                    await writer.wait_closed()
                    
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout: Could not connect to iTach at %s:%s within 5 seconds.", self.host, self.port)
            except Exception as err:
                _LOGGER.error("Error communicating with iTach at %s:%s - %s", self.host, self.port, err)
        
        return reply_str
