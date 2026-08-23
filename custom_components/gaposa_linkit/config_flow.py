import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULT_PORT
from .const import DOMAIN


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
                data=user_input,
            )

        channel_options = [
            {"value": str(i), "label": f"Channel {i}"} for i in range(1, 25)
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT
                    )
                ),
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    "channels", default=[]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=channel_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
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
                self.config_entry, data=user_input
            )
            return self.async_create_entry(title="", data={})

        # Pre-fill fields with current saved values
        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_channels = self.config_entry.data.get("channels", [])

        channel_options = [
            {"value": str(i), "label": f"Channel {i}"} for i in range(1, 25)
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT
                    )
                ),
                vol.Optional(CONF_PORT, default=current_port): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional("channels", default=current_channels): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=channel_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
