from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .channel import channel_device_info
from .channel import channel_enable_set_position
from .channel import update_channel_entry_data
from .const import CONF_CHANNELS
from .const import CONF_ENABLE_SET_POSITION
from .const import get_config_update_signal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-channel switch entities."""
    enable_set_position_config = entry.data.get(CONF_ENABLE_SET_POSITION, True)
    async_add_entities(
        [
            GaposaAllowSetPositionSwitch(
                entry,
                int(channel),
                channel_enable_set_position(enable_set_position_config, channel),
                get_config_update_signal(entry.entry_id),
            )
            for channel in entry.data.get(CONF_CHANNELS, [])
        ]
    )


class GaposaAllowSetPositionSwitch(SwitchEntity):
    """Switch entity for per-channel set-position support."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:cursor-default-click-outline"
    _attr_name = "Allow custom position"

    def __init__(
        self,
        config_entry: ConfigEntry,
        channel_id: int,
        is_on: bool,
        config_signal: str,
    ) -> None:
        """Initialize the entity."""
        self._config_entry = config_entry
        self._channel_id = channel_id
        self._channel_key = str(channel_id)
        self._config_signal = config_signal
        self._attr_device_info = channel_device_info(config_entry.entry_id, channel_id)
        self._attr_is_on = is_on
        self._attr_unique_id = (
            f"{config_entry.entry_id}_channel_{channel_id}_allow_set_position"
        )

    async def async_added_to_hass(self) -> None:
        """Register for config updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._config_signal,
                self._handle_config_update,
            )
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable set-position support."""
        self._update_value(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable set-position support."""
        self._update_value(False)

    @callback
    def _update_value(self, value: bool) -> None:
        """Persist the switch state."""
        self._attr_is_on = value
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=update_channel_entry_data(
                self._config_entry.data,
                self._channel_key,
                enable_set_position=value,
            ),
        )
        self.async_write_ha_state()

    @callback
    def _handle_config_update(self, entry_data: dict) -> None:
        """Refresh the entity after a config-entry update."""
        self._attr_is_on = channel_enable_set_position(
            entry_data.get(CONF_ENABLE_SET_POSITION, True),
            self._channel_key,
        )
        self.async_write_ha_state()
