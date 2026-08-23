from homeassistant.components.cover import CoverEntity
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_DOWN
from .const import CMD_STOP
from .const import CMD_UP
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Gaposa Cover platform."""
    hub = hass.data[DOMAIN][entry.entry_id]

    # Safely retrieve the list of enabled channels from the config flow
    enabled_channels = entry.data.get("channels", [])

    entities = []
    for ch_str in enabled_channels:
        channel_id = int(ch_str)
        if channel_id <= 8:
            bank, bank_ch = 0x00, channel_id
        elif channel_id <= 16:
            bank, bank_ch = 0x01, channel_id - 8
        else:
            bank, bank_ch = 0x02, channel_id - 16

        entities.append(GaposaCover(hub, entry.entry_id, channel_id, bank, bank_ch))

    async_add_entities(entities)

class GaposaCover(CoverEntity):
    """Representation of a Gaposa Shade Channel."""

    def __init__(self, hub, entry_id, channel_id, bank, bank_channel):
        """Initialize the cover."""
        self._hub = hub
        self._bank = bank
        self._bank_channel = bank_channel
        self._attr_unique_id = f"{entry_id}_channel_{channel_id}"
        self._attr_name = f"Gaposa Shade Channel {channel_id}"

        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

        # FIX: Define the attribute Home Assistant is looking for.
        # Starting as None means the state is unknown when HA first boots.
        self._attr_is_closed = None

        # Create a variable to hold the raw reply
        self._last_hub_reply = None

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # If there is no previous state saved in Home Assistant's history,
        # default to 'closed' (or 'open') so Matter/HomeKit sees a valid state.
        if self.state is None:
            self._attr_is_closed = True
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the entity-specific state attributes."""
        # Expose the variable to Home Assistant
        return {
            "last_hub_reply": self._last_hub_reply
        }

    async def async_open_cover(self, **kwargs):
        """Open the cover and optimistically assume it succeeded."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_UP)
        self._attr_is_closed = False
        if reply:
            self._last_hub_reply = reply
        # Tell Home Assistant the state/attributes have changed so the UI updates
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close the cover and optimistically assume it succeeded."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_DOWN)
        self._attr_is_closed = True
        if reply:
            self._last_hub_reply = reply
        # Tell Home Assistant the state/attributes have changed so the UI updates
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_STOP)
        # If we stop midway, it is partially open (which Home Assistant considers not closed)
        self._attr_is_closed = False
        if reply:
            self._last_hub_reply = reply
        # Tell Home Assistant the state/attributes have changed so the UI updates
        self.async_write_ha_state()
