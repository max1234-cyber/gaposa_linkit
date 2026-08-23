from typing import Any
from typing import Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_CHANNELS
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_PORT
from .const import DEFAULT_TRAVEL_TIME
from .const import DOMAIN

CHANNEL_RANGE = range(1, 25)


def _travel_time_key(channel: int) -> str:
    """Return the config field key for a channel travel time."""
    return f"travel_time_{channel}"


def _channel_options() -> list[selector.SelectOptionDict]:
    """Return config flow options for all supported channels."""
    return [{"value": str(i), "label": f"Channel {i}"} for i in CHANNEL_RANGE]


def _travel_time_selector() -> selector.NumberSelector:
    """Return a number selector for travel time values."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=3600,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _normalize_config_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Extract channel travel times into the stored config entry format."""
    channels = [str(channel) for channel in user_input.get(CONF_CHANNELS, [])]
    travel_times = {
        channel: int(user_input.get(_travel_time_key(int(channel)), DEFAULT_TRAVEL_TIME))
        for channel in channels
    }

    return {
        CONF_HOST: user_input[CONF_HOST],
        CONF_PORT: int(user_input.get(CONF_PORT, DEFAULT_PORT)),
        CONF_CHANNELS: channels,
        CONF_TRAVEL_TIMES: travel_times,
    }


def _build_base_schema(
    *,
    host: str = "",
    port: int = DEFAULT_PORT,
    channels: Optional[list[str]] = None,
) -> vol.Schema:
    """Build the base config schema for hub settings."""
    current_channels = channels or []
    schema: dict[Any, Any] = {
        vol.Required(CONF_HOST, default=host): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Optional(CONF_PORT, default=port): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=65535,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_CHANNELS, default=current_channels): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_channel_options(),
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }

    return vol.Schema(schema)


def _build_travel_time_schema(
    channels: list[str],
    travel_times: Optional[dict[str, int]] = None,
) -> vol.Schema:
    """Build a schema containing only travel time fields for selected channels."""
    current_travel_times = travel_times or {}
    schema: dict[Any, Any] = {}
    for channel in [int(channel_id) for channel_id in channels]:
        schema[vol.Optional(
            _travel_time_key(channel),
            default=current_travel_times.get(str(channel), DEFAULT_TRAVEL_TIME),
        )] = _travel_time_selector()

    return vol.Schema(schema)


def _build_options_schema(
    *,
    host: str,
    port: int,
    channels: list[str],
    travel_times: Optional[dict[str, int]] = None,
) -> vol.Schema:
    """Build a reconfiguration schema with channel travel times."""
    schema = dict(_build_base_schema(host=host, port=port, channels=channels).schema)
    schema.update(_build_travel_time_schema(channels, travel_times).schema)
    return vol.Schema(schema)


class GaposaLinkItConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup for Gaposa LinkIt."""

    VERSION = 1
    _pending_config: Optional[dict[str, Any]] = None

    async def async_step_user(self, user_input=None):
        """Handle the single-step initial configuration."""
        errors = {}

        if user_input is not None:
            self._pending_config = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: int(user_input.get(CONF_PORT, DEFAULT_PORT)),
                CONF_CHANNELS: [str(channel) for channel in user_input.get(CONF_CHANNELS, [])],
            }
            if not self._pending_config[CONF_CHANNELS]:
                data = {**self._pending_config, CONF_TRAVEL_TIMES: {}}
                return self.async_create_entry(
                    title=f"Gaposa LinkIt ({data[CONF_HOST]})",
                    data=data,
                )

            return await self.async_step_travel_times()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_base_schema(),
            errors=errors,
        )

    async def async_step_travel_times(self, user_input=None):
        """Collect travel times for the channels selected during setup."""
        if self._pending_config is None:
            return await self.async_step_user()

        if user_input is not None:
            data = {
                **self._pending_config,
                CONF_TRAVEL_TIMES: {
                    channel: int(
                        user_input.get(_travel_time_key(int(channel)), DEFAULT_TRAVEL_TIME)
                    )
                    for channel in self._pending_config[CONF_CHANNELS]
                },
            }
            return self.async_create_entry(
                title=f"Gaposa LinkIt ({data[CONF_HOST]})",
                data=data,
            )

        return self.async_show_form(
            step_id="travel_times",
            data_schema=_build_travel_time_schema(self._pending_config[CONF_CHANNELS]),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Attach the options flow handler to enable the Configure button."""
        # FIX: Removed config_entry argument
        return GaposaLinkItOptionsFlowHandler()


class GaposaLinkItOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle re-configuration via the 'Configure' button on the integration card."""

    # FIX: Completely removed the __init__ method since config_entry is now a native property

    async def async_step_init(self, user_input=None):
        """Manage configuration updates."""
        if user_input is not None:
            # Update the stored configuration entry with the new settings
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=_normalize_config_input(user_input),
            )
            return self.async_create_entry(title="", data={})

        # Pre-fill fields with current saved values
        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_channels = self.config_entry.data.get(CONF_CHANNELS, [])
        current_travel_times = self.config_entry.data.get(CONF_TRAVEL_TIMES, {})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(
                host=current_host,
                port=current_port,
                channels=current_channels,
                travel_times=current_travel_times,
            ),
        )
