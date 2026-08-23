from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_CHANNELS
from .const import CONF_CONNECTION_TYPE
from .const import CONF_SERIAL_PORT
from .const import CONNECTION_TYPE_IP
from .const import CONNECTION_TYPE_USB
from .const import DEFAULT_PORT
from .const import DOMAIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_config_data(
    user_input: dict,
    current_data: Mapping[str, Any] | None = None,
) -> dict:
    channels = [str(channel) for channel in user_input.get(CONF_CHANNELS, [])]
    connection_type = user_input.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_IP)

    data: dict[str, Any] = {
        CONF_CONNECTION_TYPE: connection_type,
        CONF_CHANNELS: channels,
    }

    if connection_type == CONNECTION_TYPE_USB:
        data[CONF_SERIAL_PORT] = user_input[CONF_SERIAL_PORT]
    else:
        data[CONF_HOST] = user_input[CONF_HOST]
        data[CONF_PORT] = int(user_input.get(CONF_PORT, DEFAULT_PORT))

    return data


_CONNECTION_TYPE_OPTIONS: list[selector.SelectOptionDict] = [
    {"value": CONNECTION_TYPE_IP, "label": "IP (network adapter, e.g. iTach IP2SL)"},
    {"value": CONNECTION_TYPE_USB, "label": "USB (directly attached USB-to-serial adapter)"},
]

_CHANNEL_OPTIONS: list[selector.SelectOptionDict] = [
    {"value": str(i), "label": f"Channel {i}"} for i in range(1, 25)
]


def _build_connection_type_schema(
    *,
    connection_type: str = CONNECTION_TYPE_IP,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_CONNECTION_TYPE, default=connection_type): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_CONNECTION_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _build_ip_schema(
    *,
    host: str = "",
    port: int = DEFAULT_PORT,
    channels: list[str] | None = None,
) -> vol.Schema:
    channels = channels or []
    return vol.Schema(
        {
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
                    options=_CHANNEL_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _build_usb_schema(
    *,
    serial_port: str = "",
    channels: list[str] | None = None,
) -> vol.Schema:
    channels = channels or []
    return vol.Schema(
        {
            vol.Required(CONF_SERIAL_PORT, default=serial_port): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_CHANNELS, default=channels): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_CHANNEL_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


class GaposaLinkItConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup for Gaposa LinkIt."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection_type: str = CONNECTION_TYPE_IP

    async def async_step_user(self, user_input=None):
        """Ask the user to choose a connection type (IP or USB)."""
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_TYPE_USB:
                return await self.async_step_usb()
            return await self.async_step_ip()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_connection_type_schema(),
        )

    async def async_step_ip(self, user_input=None):
        """Configure IP connection details."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_IP
            host_ip = user_input.get(CONF_HOST, "Hub")
            return self.async_create_entry(
                title=f"Gaposa LinkIt ({host_ip})",
                data=_normalize_config_data(user_input),
            )

        return self.async_show_form(
            step_id="ip",
            data_schema=_build_ip_schema(),
        )

    async def async_step_usb(self, user_input=None):  # type: ignore[override]
        """Configure USB connection details."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_USB
            serial_port = user_input.get(CONF_SERIAL_PORT, "USB")
            return self.async_create_entry(
                title=f"Gaposa LinkIt ({serial_port})",
                data=_normalize_config_data(user_input),
            )

        return self.async_show_form(
            step_id="usb",
            data_schema=_build_usb_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # type: ignore[override]
        """Attach the options flow handler to enable the Configure button."""
        return GaposaLinkItOptionsFlowHandler()


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


class GaposaLinkItOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle re-configuration via the 'Configure' button on the integration card."""

    async def async_step_init(self, user_input=None):
        """Ask whether to switch connection type or go straight to settings."""
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_TYPE_USB:
                return await self.async_step_usb()
            return await self.async_step_ip()

        current_type = self.config_entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_IP)
        return self.async_show_form(
            step_id="init",
            data_schema=_build_connection_type_schema(connection_type=current_type),
        )

    async def async_step_ip(self, user_input=None):
        """Reconfigure IP connection details."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_IP
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=_normalize_config_data(user_input, self.config_entry.data),
            )
            return self.async_create_entry(title="", data={})

        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_channels = self.config_entry.data.get(CONF_CHANNELS, [])

        return self.async_show_form(
            step_id="ip",
            data_schema=_build_ip_schema(
                host=current_host,
                port=current_port,
                channels=current_channels,
            ),
        )

    async def async_step_usb(self, user_input=None):
        """Reconfigure USB connection details."""
        if user_input is not None:
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_USB
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=_normalize_config_data(user_input, self.config_entry.data),
            )
            return self.async_create_entry(title="", data={})

        current_serial_port = self.config_entry.data.get(CONF_SERIAL_PORT, "")
        current_channels = self.config_entry.data.get(CONF_CHANNELS, [])

        return self.async_show_form(
            step_id="usb",
            data_schema=_build_usb_schema(
                serial_port=current_serial_port,
                channels=current_channels,
            ),
        )
