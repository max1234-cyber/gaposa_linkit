"""Tests for the Gaposa LinkIt config flow."""
from unittest.mock import MagicMock

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.gaposa_linkit.const import CONF_BAUD_RATE
from custom_components.gaposa_linkit.const import CONF_CHANNELS
from custom_components.gaposa_linkit.const import CONF_CONNECTION_TYPE
from custom_components.gaposa_linkit.const import CONF_SERIAL_PORT
from custom_components.gaposa_linkit.const import CONNECTION_TYPE_IP
from custom_components.gaposa_linkit.const import CONNECTION_TYPE_USB


def _schema_keys(result: dict) -> set[str]:
    return {key.schema for key in result["data_schema"].schema}


# ---------------------------------------------------------------------------
# Config flow – user step (connection type selector)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant):
    """Test the user step shows only the connection type selector."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert _schema_keys(result) == {CONF_CONNECTION_TYPE}


@pytest.mark.asyncio
async def test_config_flow_user_step_selects_ip(hass: HomeAssistant):
    """Selecting IP from the user step redirects to the ip step."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input={CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP})

    assert result["type"] == "form"
    assert result["step_id"] == "ip"
    assert _schema_keys(result) == {CONF_HOST, CONF_PORT, CONF_CHANNELS}


@pytest.mark.asyncio
async def test_config_flow_user_step_selects_usb(hass: HomeAssistant):
    """Selecting USB from the user step redirects to the usb step."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input={CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB})

    assert result["type"] == "form"
    assert result["step_id"] == "usb"
    assert _schema_keys(result) == {CONF_SERIAL_PORT, CONF_BAUD_RATE, CONF_CHANNELS}


# ---------------------------------------------------------------------------
# Config flow – IP step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_flow_ip_step_with_input(hass: HomeAssistant):
    """Test the ip step creates an entry with correct data."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2", "3"],
    }

    result = await flow.async_step_ip(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["title"] == "Gaposa LinkIt (192.168.1.100)"
    assert result["data"] == {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2", "3"],
    }


@pytest.mark.asyncio
async def test_config_flow_ip_step_with_default_port(hass: HomeAssistant):
    """Test the ip step uses the default port when not supplied."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_CHANNELS: [],
    }

    result = await flow.async_step_ip(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_CONNECTION_TYPE] == CONNECTION_TYPE_IP
    assert result["data"][CONF_HOST] == "192.168.1.100"
    assert result["data"][CONF_PORT] == 4999


# ---------------------------------------------------------------------------
# Config flow – USB step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_flow_usb_step_with_input(hass: HomeAssistant):
    """Test the usb step creates an entry with correct data."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_SERIAL_PORT: "/dev/ttyUSB0",
        CONF_BAUD_RATE: 9600,
        CONF_CHANNELS: ["1", "2"],
    }

    result = await flow.async_step_usb(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["title"] == "Gaposa LinkIt (/dev/ttyUSB0)"
    assert result["data"] == {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB,
        CONF_SERIAL_PORT: "/dev/ttyUSB0",
        CONF_BAUD_RATE: 9600,
        CONF_CHANNELS: ["1", "2"],
    }


@pytest.mark.asyncio
async def test_config_flow_usb_step_with_default_baud_rate(hass: HomeAssistant):
    """Test the usb step uses the default baud rate when not supplied."""
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItConfigFlow

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_SERIAL_PORT: "/dev/ttyUSB0",
        CONF_CHANNELS: [],
    }

    result = await flow.async_step_usb(user_input=user_input)

    assert result["type"] == "create_entry"
    assert result["data"][CONF_CONNECTION_TYPE] == CONNECTION_TYPE_USB
    assert result["data"][CONF_BAUD_RATE] == 9600


# ---------------------------------------------------------------------------
# Options flow – init step (connection type selector)
# ---------------------------------------------------------------------------


def _make_options_flow(hass, data):
    from custom_components.gaposa_linkit.config_flow import GaposaLinkItOptionsFlowHandler

    config_entry = MagicMock()
    config_entry.entry_id = "test-entry-id"
    config_entry.data = data
    hass.config_entries.async_get_known_entry = MagicMock(return_value=config_entry)
    flow = GaposaLinkItOptionsFlowHandler()
    flow.handler = config_entry.entry_id
    flow._config_entry = config_entry
    flow.hass = hass
    return flow, config_entry


@pytest.mark.asyncio
async def test_options_flow_init(hass: HomeAssistant):
    """Test the init step shows the connection type selector."""
    flow, _ = _make_options_flow(
        hass,
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 4999,
            CONF_CHANNELS: ["1", "2"],
        },
    )

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert _schema_keys(result) == {CONF_CONNECTION_TYPE}


@pytest.mark.asyncio
async def test_options_flow_init_selects_ip(hass: HomeAssistant):
    """Selecting IP from options init redirects to the ip step."""
    flow, _ = _make_options_flow(
        hass,
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 4999,
            CONF_CHANNELS: ["1", "2"],
        },
    )

    result = await flow.async_step_init(user_input={CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP})

    assert result["type"] == "form"
    assert result["step_id"] == "ip"


@pytest.mark.asyncio
async def test_options_flow_init_selects_usb(hass: HomeAssistant):
    """Selecting USB from options init redirects to the usb step."""
    flow, _ = _make_options_flow(
        hass,
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUD_RATE: 9600,
            CONF_CHANNELS: ["1"],
        },
    )

    result = await flow.async_step_init(user_input={CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB})

    assert result["type"] == "form"
    assert result["step_id"] == "usb"


@pytest.mark.asyncio
async def test_options_flow_ip_with_input(hass: HomeAssistant):
    """Test the options ip step updates the config entry."""
    flow, config_entry = _make_options_flow(
        hass,
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 4999,
            CONF_CHANNELS: ["1", "2"],
        },
    )

    user_input = {
        CONF_HOST: "192.168.1.101",
        CONF_PORT: 5000,
        CONF_CHANNELS: ["1", "2", "3"],
    }

    result = await flow.async_step_ip(user_input=user_input)

    assert result["type"] == "create_entry"
    hass.config_entries.async_update_entry.assert_called_once_with(
        config_entry,
        data={
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
            CONF_HOST: "192.168.1.101",
            CONF_PORT: 5000,
            CONF_CHANNELS: ["1", "2", "3"],
        },
    )


@pytest.mark.asyncio
async def test_options_flow_usb_with_input(hass: HomeAssistant):
    """Test the options usb step updates the config entry."""
    flow, config_entry = _make_options_flow(
        hass,
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUD_RATE: 9600,
            CONF_CHANNELS: ["1"],
        },
    )

    user_input = {
        CONF_SERIAL_PORT: "/dev/ttyUSB1",
        CONF_BAUD_RATE: 19200,
        CONF_CHANNELS: ["1", "2"],
    }

    result = await flow.async_step_usb(user_input=user_input)

    assert result["type"] == "create_entry"
    hass.config_entries.async_update_entry.assert_called_once_with(
        config_entry,
        data={
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_USB,
            CONF_SERIAL_PORT: "/dev/ttyUSB1",
            CONF_BAUD_RATE: 19200,
            CONF_CHANNELS: ["1", "2"],
        },
    )

