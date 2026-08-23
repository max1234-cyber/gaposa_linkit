import asyncio
from contextlib import suppress
from time import monotonic
from typing import Optional

from homeassistant.components.cover import ATTR_POSITION
from homeassistant.components.cover import CoverEntity
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_DOWN
from .const import CMD_STOP
from .const import CMD_UP
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_TRAVEL_TIME
from .const import DOMAIN

POSITION_UPDATE_INTERVAL = 1.0
POSITION_REFRESH_INTERVAL = 0.001


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Gaposa Cover platform."""
    hub = hass.data[DOMAIN][entry.entry_id]

    # Safely retrieve the list of enabled channels from the config flow
    enabled_channels = entry.data.get("channels", [])
    travel_times = entry.data.get(CONF_TRAVEL_TIMES, {})

    entities = []
    for ch_str in enabled_channels:
        channel_id = int(ch_str)
        if channel_id <= 8:
            bank, bank_ch = 0x00, channel_id
        elif channel_id <= 16:
            bank, bank_ch = 0x01, channel_id - 8
        else:
            bank, bank_ch = 0x02, channel_id - 16

        entities.append(
            GaposaCover(
                hub,
                entry.entry_id,
                channel_id,
                bank,
                bank_ch,
                travel_time=travel_times.get(ch_str, DEFAULT_TRAVEL_TIME),
            )
        )

    async_add_entities(entities)


class GaposaCover(CoverEntity):
    """Representation of a Gaposa Shade Channel."""

    def __init__(self, hub, entry_id, channel_id, bank, bank_channel, *, travel_time=60):
        """Initialize the cover."""
        self._hub = hub
        self._bank = bank
        self._bank_channel = bank_channel
        self._travel_time = float(travel_time if travel_time > 0 else DEFAULT_TRAVEL_TIME)
        self._attr_unique_id = f"{entry_id}_channel_{channel_id}"
        self._attr_name = f"Gaposa Shade Channel {channel_id}"

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        self._attr_is_closed = True

        # Create a dict to hold the raw reply as an extra state attribute
        self._attr_extra_state_attributes: dict = {"last_hub_reply": None}
        self._current_position = 0.0
        self._motion_direction: Optional[str] = None
        self._motion_duration = 0.0
        self._motion_started_at: Optional[float] = None
        self._motion_start_position = 0.0
        self._motion_target_position = 0.0
        self._motion_task: Optional[asyncio.Task] = None
        self._stop_when_complete = False
        self._last_refresh_at: Optional[float] = None
        self._last_refresh_complete = False

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        self._update_is_closed()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Clean up background tasks when the entity is unloaded."""
        await self._cancel_motion_task()
        await super().async_will_remove_from_hass()

    @property
    def current_cover_position(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current estimated cover position."""
        self._refresh_position()
        return int(round(self._current_position))

    @property
    def is_opening(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if the cover is currently opening."""
        self._refresh_position()
        return self._motion_direction == "opening"

    @property
    def is_closing(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if the cover is currently closing."""
        self._refresh_position()
        return self._motion_direction == "closing"

    async def async_open_cover(self, **kwargs):
        """Open the cover and optimistically assume it succeeded."""
        await self._move_cover(CMD_UP, 100, "opening")

    async def async_close_cover(self, **kwargs):
        """Close the cover and optimistically assume it succeeded."""
        await self._move_cover(CMD_DOWN, 0, "closing")

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._refresh_position()
        await self._cancel_motion_task()
        reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_STOP)
        self._clear_motion_state()
        if reply:
            self._attr_extra_state_attributes = {"last_hub_reply": reply}
        self._update_is_closed()
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a requested position."""
        target_position = max(0, min(100, int(kwargs[ATTR_POSITION])))
        self._refresh_position()

        if target_position == int(round(self._current_position)):
            self.async_write_ha_state()
            return

        direction = "opening" if target_position > self._current_position else "closing"
        command = CMD_UP if direction == "opening" else CMD_DOWN
        await self._move_cover(
            command,
            target_position,
            direction,
            stop_when_complete=target_position not in (0, 100),
        )

    async def _move_cover(
        self,
        command: int,
        target_position: int,
        direction: str,
        *,
        stop_when_complete: bool = False,
    ) -> None:
        """Send a move command and start optimistic position tracking."""
        self._refresh_position()
        await self._cancel_motion_task()

        reply = await self._hub.send_command(self._bank, self._bank_channel, command)
        if reply:
            self._attr_extra_state_attributes = {"last_hub_reply": reply}

        self._start_motion(target_position, direction, stop_when_complete=stop_when_complete)
        self.async_write_ha_state()

    def _start_motion(
        self,
        target_position: int,
        direction: str,
        *,
        stop_when_complete: bool = False,
    ) -> None:
        """Start optimistic motion tracking toward a target position."""
        self._motion_direction = direction
        self._motion_started_at = monotonic()
        self._motion_start_position = self._current_position
        self._motion_target_position = float(target_position)
        self._motion_duration = (
            abs(self._motion_target_position - self._motion_start_position) / 100
        ) * self._travel_time
        self._stop_when_complete = stop_when_complete
        self._last_refresh_at = None
        self._last_refresh_complete = False
        self._update_is_closed()

        if self._motion_duration <= 0:
            self._current_position = self._motion_target_position
            self._clear_motion_state()
            self._update_is_closed()
            return

        self._motion_task = asyncio.create_task(self._run_motion())

    async def _run_motion(self) -> None:
        """Update the optimistic position while the cover is moving."""
        task = asyncio.current_task()
        try:
            while self._motion_task is task and not self._refresh_position():
                self.async_write_ha_state()
                await asyncio.sleep(POSITION_UPDATE_INTERVAL)

            if self._motion_task is not task:
                return

            if self._stop_when_complete:
                reply = await self._hub.send_command(self._bank, self._bank_channel, CMD_STOP)
                if reply:
                    self._attr_extra_state_attributes = {"last_hub_reply": reply}

            self._clear_motion_state()
            self._update_is_closed()
            self.async_write_ha_state()
        except asyncio.CancelledError:
            raise
        finally:
            if self._motion_task is task:
                self._motion_task = None

    def _refresh_position(self) -> bool:
        """Update the current position from elapsed motion time."""
        now = monotonic()
        if (
            self._last_refresh_at is not None
            and now - self._last_refresh_at < POSITION_REFRESH_INTERVAL
        ):
            return self._last_refresh_complete

        if self._motion_direction is None or self._motion_started_at is None:
            self._last_refresh_at = now
            self._last_refresh_complete = False
            self._update_is_closed()
            return False

        if self._motion_duration <= 0:
            self._current_position = self._motion_target_position
            self._last_refresh_at = now
            self._last_refresh_complete = True
            self._update_is_closed()
            return True

        elapsed = now - self._motion_started_at
        progress = min(max(elapsed / self._motion_duration, 0.0), 1.0)
        self._current_position = self._motion_start_position + (
            (self._motion_target_position - self._motion_start_position) * progress
        )
        self._last_refresh_at = now
        self._last_refresh_complete = progress >= 1.0
        self._update_is_closed()
        return self._last_refresh_complete

    def _clear_motion_state(self) -> None:
        """Clear active motion tracking state."""
        self._motion_direction = None
        self._motion_duration = 0.0
        self._motion_started_at = None
        self._motion_start_position = self._current_position
        self._motion_target_position = self._current_position
        self._stop_when_complete = False
        self._last_refresh_at = None
        self._last_refresh_complete = False

    def _update_is_closed(self) -> None:
        """Update the Home Assistant closed flag from the current position."""
        self._attr_is_closed = (
            self._motion_direction != "opening" and int(round(self._current_position)) == 0
        )

    async def _cancel_motion_task(self) -> None:
        """Cancel the current motion task, if any."""
        task = self._motion_task
        if task is None:
            return

        self._motion_task = None
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
