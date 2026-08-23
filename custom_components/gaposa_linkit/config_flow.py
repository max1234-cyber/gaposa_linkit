from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_CHANNELS
from .const import CONF_ENABLE_SET_POSITION
from .const import CONF_TRAVEL_TIMES
from .const import DEFAULT_PORT
from .const import DEFAULT_TRAVEL_TIME
from .const import DOMAIN


def _travel_time_field(channel: str) -> str:
    return f"travel_time_{channel}"


def _normalize_travel_time(value) -> int:
    return max(1, int(value))


def _normalize_config_data(
    user_input: dict,
    current_data: Mapping[str, Any] | None = None,
) -> dict:
    current_data = current_data or {}
    channels = [str(channel) for channel in user_input.get(CONF_CHANNELS, [])]
    current_travel_times = current_data.get(CONF_TRAVEL_TIMES, {})

    travel_times = {
        channel: _normalize_travel_time(
            user_input.get(
                _travel_time_field(channel),
                current_travel_times.get(channel, DEFAULT_TRAVEL_TIME),
            )
        )
        for channel in channels
    }

    return {
        CONF_HOST: user_input[CONF_HOST],
        CONF_PORT: int(user_input.get(CONF_PORT, DEFAULT_PORT)),
        CONF_CHANNELS: channels,
        CONF_ENABLE_SET_POSITION: user_input.get(CONF_ENABLE_SET_POSITION, True),
        CONF_TRAVEL_TIMES: travel_times,
    }


def _build_schema(
    *,
    host: str = "",
    port: int = DEFAULT_PORT,
    channels: list[str] | None = None,
    enable_set_position: bool = True,
    travel_times: dict[str, int] | None = None,
) -> vol.Schema:
    channels = channels or []
    travel_times = travel_times or {}

    channel_options: list[selector.SelectOptionDict] = [
        {"value": str(i), "label": f"Channel {i}"} for i in range(1, 25)
    ]

    schema_fields: dict = {
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
        vol.Optional(CONF_CHANNELS, default=channels): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=channel_options,
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(
            CONF_ENABLE_SET_POSITION,
            default=enable_set_position,
        ): selector.BooleanSelector(),
    }

    for channel in channels:
        schema_fields[
            vol.Optional(
                _travel_time_field(channel),
                default=travel_times.get(channel, DEFAULT_TRAVEL_TIME),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=3600,
                mode=selector.NumberSelectorMode.BOX,
            )
        )

    return vol.Schema(schema_fields)


class GaposaLinkItConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup for Gaposa LinkIt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the single-step initial configuration."""
        errors = {}

        if user_input is not None:
            host_ip = user_input.get(CONF_HOST, "Hub")
            return self.async_create_entry(
                title=f"Gaposa LinkIt ({host_ip})",
                data=_normalize_config_data(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors=errors,
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
                data=_normalize_config_data(user_input, self.config_entry.data),
            )
            return self.async_create_entry(title="", data={})

        # Pre-fill fields with current saved values
        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_channels = self.config_entry.data.get(CONF_CHANNELS, [])
        current_enable_set_position = self.config_entry.data.get(
            CONF_ENABLE_SET_POSITION,
            True,
        )
        current_travel_times = self.config_entry.data.get(CONF_TRAVEL_TIMES, {})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                host=current_host,
                port=current_port,
                channels=current_channels,
                enable_set_position=current_enable_set_position,
                travel_times=current_travel_times,
            ),
        )
