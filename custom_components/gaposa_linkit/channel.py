from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_CHANNELS
from .const import CONF_ENABLE_SET_POSITION
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_TRAVEL_TIME
from .const import DOMAIN


def channel_name(channel_id: int) -> str:
    """Return the user-facing name for a channel."""
    return f"Channel {channel_id}"


def channel_unique_base(entry_id: str, channel_id: int) -> str:
    """Return the shared unique-id prefix for a channel device."""
    return f"{entry_id}_channel_{channel_id}"


def channel_device_info(entry_id: str, channel_id: int) -> DeviceInfo:
    """Return device metadata for a channel."""
    return DeviceInfo(
        identifiers={(DOMAIN, channel_unique_base(entry_id, channel_id))},
        manufacturer="Gaposa",
        model="LinkIt Hub Shade Channel",
        name=channel_name(channel_id),
    )


def channel_bank_address(channel_id: int) -> tuple[int, int]:
    """Return the hub bank and bank-local channel number."""
    if channel_id <= 8:
        return 0x00, channel_id
    if channel_id <= 16:
        return 0x01, channel_id - 8
    return 0x02, channel_id - 16


def normalize_travel_time(value: int | float) -> int:
    """Return a safe travel time value."""
    return max(1, int(value))


def channel_enable_set_position(
    config_value: dict[str, bool] | bool,
    channel_key: str,
) -> bool:
    """Return whether set-position is enabled for a channel."""
    if isinstance(config_value, dict):
        return bool(config_value.get(channel_key, True))
    return bool(config_value)


def update_channel_entry_data(
    entry_data: Mapping[str, Any],
    channel_key: str,
    *,
    enable_set_position: bool | None = None,
    travel_time: int | float | None = None,
) -> dict[str, Any]:
    """Return updated config-entry data for a single channel."""
    updated_data = dict(entry_data)
    channels = [str(channel) for channel in entry_data.get(CONF_CHANNELS, [])]

    current_enable_set_position = entry_data.get(CONF_ENABLE_SET_POSITION, True)
    enable_set_position_data = {
        channel: channel_enable_set_position(current_enable_set_position, channel)
        for channel in channels
    }
    if enable_set_position is not None:
        enable_set_position_data[channel_key] = bool(enable_set_position)

    travel_times = {
        str(channel): normalize_travel_time(value)
        for channel, value in dict(entry_data.get(CONF_TRAVEL_TIMES, {})).items()
    }
    if travel_time is not None:
        travel_times[channel_key] = normalize_travel_time(travel_time)

    for channel in channels:
        travel_times.setdefault(channel, DEFAULT_TRAVEL_TIME)

    updated_data[CONF_ENABLE_SET_POSITION] = enable_set_position_data
    updated_data[CONF_TRAVEL_TIMES] = travel_times
    return updated_data
