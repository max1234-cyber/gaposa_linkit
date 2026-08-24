from homeassistant.components.number import NumberEntity
from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .channel import channel_device_info
from .channel import normalize_travel_time
from .channel import update_channel_entry_data
from .const import CONF_CHANNELS
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_TRAVEL_TIME
from .const import get_config_update_signal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-channel number entities."""
    travel_times = entry.data.get(CONF_TRAVEL_TIMES, {})
    async_add_entities(
        [
            GaposaTravelTimeNumber(
                entry,
                int(channel),
                travel_times.get(str(channel), DEFAULT_TRAVEL_TIME),
                get_config_update_signal(entry.entry_id),
            )
            for channel in entry.data.get(CONF_CHANNELS, [])
        ]
    )


class GaposaTravelTimeNumber(NumberEntity):
    """Number entity for per-channel travel time."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX
    _attr_name = "Travel time"
    _attr_native_max_value = 3600
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(
        self,
        config_entry: ConfigEntry,
        channel_id: int,
        travel_time: int,
        config_signal: str,
    ) -> None:
        """Initialize the entity."""
        self._config_entry = config_entry
        self._channel_id = channel_id
        self._channel_key = str(channel_id)
        self._config_signal = config_signal
        self._attr_device_info = channel_device_info(config_entry.entry_id, channel_id)
        self._attr_unique_id = f"{config_entry.entry_id}_channel_{channel_id}_travel_time"
        self._attr_native_value = normalize_travel_time(travel_time)

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

    async def async_set_native_value(self, value: float) -> None:
        """Persist a new travel-time value."""
        self._attr_native_value = normalize_travel_time(value)
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=update_channel_entry_data(
                self._config_entry.data,
                self._channel_key,
                travel_time=self._attr_native_value,
            ),
        )
        self.async_write_ha_state()

    @callback
    def _handle_config_update(self, entry_data: dict) -> None:
        """Refresh the entity after a config-entry update."""
        self._attr_native_value = normalize_travel_time(
            entry_data.get(CONF_TRAVEL_TIMES, {}).get(
                self._channel_key,
                DEFAULT_TRAVEL_TIME,
            )
        )
        self.async_write_ha_state()
