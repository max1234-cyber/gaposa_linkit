from asyncio import CancelledError
from asyncio import Task
from asyncio import create_task
from asyncio import sleep
from time import monotonic

from homeassistant.components.cover import CoverEntity
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .channel import channel_bank_address
from .channel import channel_device_info
from .channel import channel_enable_set_position
from .channel import normalize_travel_time
from .const import CMD_DOWN
from .const import CMD_STOP
from .const import CMD_UP
from .const import CONF_CHANNELS
from .const import CONF_ENABLE_SET_POSITION
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_TRAVEL_TIME
from .const import DOMAIN
from .const import get_config_update_signal

MOTION_OPENING = "opening"
MOTION_CLOSING = "closing"
MOTION_STOPPED = "stopped"


def _clamp_position(position: float) -> float:
    return max(0.0, min(100.0, position))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Gaposa Cover platform."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    hub = runtime_data["hub"]

    enabled_channels = entry.data.get(CONF_CHANNELS, [])
    travel_times = entry.data.get(CONF_TRAVEL_TIMES, {})
    enable_set_position_config = entry.data.get(CONF_ENABLE_SET_POSITION, True)

    entities = []
    for ch_str in enabled_channels:
        channel_id = int(ch_str)
        bank, bank_ch = channel_bank_address(channel_id)

        entities.append(
            GaposaCover(
                hub,
                entry,
                channel_id,
                bank,
                bank_ch,
                travel_time=travel_times.get(ch_str, DEFAULT_TRAVEL_TIME),
                enable_set_position=channel_enable_set_position(
                    enable_set_position_config,
                    ch_str,
                ),
                config_signal=get_config_update_signal(entry.entry_id),
            )
        )

    async_add_entities(entities)


class GaposaCover(CoverEntity):
    """Representation of a Gaposa Shade Channel."""

    def __init__(
        self,
        hub,
        config_entry: ConfigEntry,
        channel_id,
        bank,
        bank_channel,
        *,
        travel_time: int = DEFAULT_TRAVEL_TIME,
        enable_set_position: bool = True,
        config_signal: str | None = None,
    ):
        """Initialize the cover."""
        self._hub = hub
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._channel_id = channel_id
        self._channel_key = str(channel_id)
        self._bank = bank
        self._bank_channel = bank_channel
        self._travel_time = normalize_travel_time(travel_time)
        self._enable_set_position = enable_set_position
        self._config_signal = config_signal or get_config_update_signal(self._entry_id)
        self._position = 0.0
        self._motion_state = MOTION_STOPPED
        self._motion_start_time: float | None = None
        self._motion_start_position = 0.0
        self._target_position = 0.0
        self._send_stop_at_target = False
        self._motion_task: Task | None = None
        self._attr_unique_id = f"{self._entry_id}_channel_{channel_id}"
        self._attr_has_entity_name = True
        self._attr_name = "Shade"
        self._attr_device_info = channel_device_info(self._entry_id, channel_id)
        self._attr_is_closed = None
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._attr_current_cover_position = 0
        self._attr_extra_state_attributes: dict = {"last_hub_reply": None}
        self._update_supported_features()

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._config_signal,
                self._handle_config_update,
            )
        )

        if self._attr_is_closed is None:
            self._sync_state()
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Clean up background tasks before removing the entity."""
        await self._cancel_motion_task()

    async def async_open_cover(self, **kwargs):
        """Open the cover and optimistically assume it succeeded."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_UP)
        self._store_reply(reply)
        await self._start_motion(MOTION_OPENING, 100.0)
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close the cover and optimistically assume it succeeded."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_DOWN)
        self._store_reply(reply)
        await self._start_motion(MOTION_CLOSING, 0.0)
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_STOP)
        self._store_reply(reply)
        await self._freeze_motion()
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a requested position."""
        target_position = int(round(_clamp_position(float(kwargs["position"]))))
        current_position = self._calculate_position()
        current_position_int = int(round(current_position))

        if target_position == current_position_int:
            return

        send_stop_at_target = 0 < target_position < 100 and self._enable_set_position

        if target_position > current_position_int:
            reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_UP)
            self._store_reply(reply)
            await self._start_motion(
                MOTION_OPENING,
                float(target_position if send_stop_at_target else 100),
                send_stop_at_target=send_stop_at_target,
            )
        else:
            reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_DOWN)
            self._store_reply(reply)
            await self._start_motion(
                MOTION_CLOSING,
                float(target_position if send_stop_at_target else 0),
                send_stop_at_target=send_stop_at_target,
            )

        self.async_write_ha_state()

    @callback
    def _handle_config_update(self, entry_data: dict) -> None:
        """Apply updated entry data without recreating the entity."""
        current_position = self._calculate_position()
        self._position = current_position
        if self._motion_state != MOTION_STOPPED:
            self._motion_start_position = current_position
            self._motion_start_time = monotonic()

        self._travel_time = normalize_travel_time(
            entry_data.get(CONF_TRAVEL_TIMES, {}).get(
                self._channel_key,
                DEFAULT_TRAVEL_TIME,
            )
        )
        self._enable_set_position = channel_enable_set_position(
            entry_data.get(CONF_ENABLE_SET_POSITION, True),
            self._channel_key,
        )
        self._update_supported_features()
        self._sync_state()
        self.async_write_ha_state()

    def _update_supported_features(self) -> None:
        features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )
        if self._enable_set_position:
            features |= CoverEntityFeature.SET_POSITION
        self._attr_supported_features = features

    def _calculate_position(self) -> float:
        if self._motion_state == MOTION_STOPPED or self._motion_start_time is None:
            return _clamp_position(self._position)

        elapsed_seconds = max(0.0, monotonic() - self._motion_start_time)
        traveled_percent = (elapsed_seconds / self._travel_time) * 100

        if self._motion_state == MOTION_OPENING:
            return _clamp_position(
                min(self._motion_start_position + traveled_percent, self._target_position)
            )

        return _clamp_position(
            max(self._motion_start_position - traveled_percent, self._target_position)
        )

    def _sync_state(self) -> None:
        current_position = self._calculate_position()
        if self._motion_state == MOTION_STOPPED:
            self._position = current_position
        self._attr_current_cover_position = int(round(current_position))
        self._attr_is_closed = current_position <= 0 and self._motion_state == MOTION_STOPPED
        self._attr_is_opening = self._motion_state == MOTION_OPENING
        self._attr_is_closing = self._motion_state == MOTION_CLOSING

    def _store_reply(self, reply: str | None) -> None:
        self._attr_extra_state_attributes = {"last_hub_reply": reply}

    async def _start_motion(
        self,
        direction: str,
        target_position: float,
        *,
        send_stop_at_target: bool = False,
    ) -> None:
        current_position = self._calculate_position()
        await self._cancel_motion_task()
        self._position = current_position
        self._motion_state = direction
        self._motion_start_position = current_position
        self._target_position = _clamp_position(target_position)
        self._motion_start_time = monotonic()
        self._send_stop_at_target = send_stop_at_target
        self._sync_state()
        self._motion_task = create_task(self._run_motion_timer())

    async def _freeze_motion(self) -> None:
        self._position = self._calculate_position()
        await self._cancel_motion_task()
        self._motion_state = MOTION_STOPPED
        self._motion_start_time = None
        self._motion_start_position = self._position
        self._target_position = self._position
        self._send_stop_at_target = False
        self._sync_state()

    async def _cancel_motion_task(self) -> None:
        motion_task = self._motion_task
        self._motion_task = None
        if motion_task is None or motion_task.done():
            return

        motion_task.cancel()
        try:
            await motion_task
        except CancelledError:
            pass

    async def _run_motion_timer(self) -> None:
        """Update position during motion until the destination is reached."""
        try:
            while self._motion_state != MOTION_STOPPED:
                current_position = self._calculate_position()
                remaining_percent = abs(self._target_position - current_position)
                if remaining_percent < 0.5:
                    await self._finish_motion()
                    self.async_write_ha_state()
                    return

                self._sync_state()
                self.async_write_ha_state()
                remaining_seconds = (remaining_percent / 100) * self._travel_time
                await sleep(min(1.0, max(0.1, remaining_seconds)))
        except CancelledError:
            raise

    async def _finish_motion(self) -> None:
        """Finalize motion when the target position is reached."""
        target_position = self._target_position
        send_stop_at_target = self._send_stop_at_target

        if send_stop_at_target:
            reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_STOP)
            self._store_reply(reply)

        self._motion_task = None
        self._position = target_position
        self._motion_state = MOTION_STOPPED
        self._motion_start_time = None
        self._motion_start_position = target_position
        self._target_position = target_position
        self._send_stop_at_target = False
        self._sync_state()
