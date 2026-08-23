"""Tests for the Gaposa LinkIt config flow."""
from unittest.mock import MagicMock

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.gaposa_linkit.const import CONF_CHANNELS
from custom_components.gaposa_linkit.const import CONF_ENABLE_SET_POSITION
from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES
from custom_components.gaposa_linkit.const import DEFAULT_TRAVEL_TIME


def _schema_keys(result: dict) -> set[str]:
    return {key.schema for key in result["data_schema"].schema}


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant):
    """Test the user step of the config flow."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert _schema_keys(result) == {
        CONF_HOST,
        CONF_PORT,
        CONF_CHANNELS,
    }


@pytest.mark.asyncio
async def test_config_flow_user_step_with_input(hass: HomeAssistant):
    """Test the user step with valid input."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2", "3"],
    }

    result = await flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["title"] == "Gaposa LinkIt (192.168.1.100)"
    assert result["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2", "3"],
        CONF_ENABLE_SET_POSITION: {
            "1": True,
            "2": True,
            "3": True,
        },
        CONF_TRAVEL_TIMES: {
            "1": DEFAULT_TRAVEL_TIME,
            "2": DEFAULT_TRAVEL_TIME,
            "3": DEFAULT_TRAVEL_TIME,
        },
    }


@pytest.mark.asyncio
async def test_config_flow_user_step_with_default_port(hass: HomeAssistant):
    """Test the user step with default port."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_CHANNELS: [],
    }

    result = await flow.async_step_user(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "192.168.1.100"
    assert result["data"][CONF_PORT] == 4999
    assert result["data"][CONF_ENABLE_SET_POSITION] == {}
    assert result["data"][CONF_TRAVEL_TIMES] == {}


@pytest.mark.asyncio
async def test_options_flow_init(hass: HomeAssistant):
    """Test the init step of the options flow."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test-entry-id"
    config_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2"],
        CONF_ENABLE_SET_POSITION: True,
        CONF_TRAVEL_TIMES: {"1": 30, "2": 45},
    }
    hass.config_entries.async_get_known_entry = MagicMock(return_value=config_entry)
    flow = GaposaLinkItOptionsFlowHandler()
    flow.handler = config_entry.entry_id
    flow._config_entry = config_entry
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert _schema_keys(result) == {
        CONF_HOST,
        CONF_PORT,
        CONF_CHANNELS,
        "channel_1",
        "channel_2",
    }


@pytest.mark.asyncio
async def test_options_flow_init_with_input(hass: HomeAssistant):
    """Test the init step with updated travel times and toggle."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test-entry-id"
    config_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2"],
        CONF_ENABLE_SET_POSITION: {"1": True, "2": True},
        CONF_TRAVEL_TIMES: {"1": 60, "2": 60},
    }
    hass.config_entries.async_get_known_entry = MagicMock(return_value=config_entry)
    flow = GaposaLinkItOptionsFlowHandler()
    flow.handler = config_entry.entry_id
    flow._config_entry = config_entry
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.101",
        CONF_PORT: 5000,
        CONF_CHANNELS: ["1", "2", "3"],
        "channel_1": {
            "allow_set_position": False,
            "travel_time": 30,
        },
        "channel_2": {
            "allow_set_position": False,
            "travel_time": 45,
        },
    }

    result = await flow.async_step_init(user_input=user_input)

    assert result["type"] == "create_entry"
    hass.config_entries.async_update_entry.assert_called_once_with(
        config_entry,
        data={
            CONF_HOST: "192.168.1.101",
            CONF_PORT: 5000,
            CONF_CHANNELS: ["1", "2", "3"],
            CONF_ENABLE_SET_POSITION: {"1": False, "2": False, "3": True},
            CONF_TRAVEL_TIMES: {"1": 30, "2": 45, "3": DEFAULT_TRAVEL_TIME},
        },
    )
