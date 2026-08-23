"""Tests for the Gaposa LinkIt integration."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_gaposa_hub():
    """Create a mock Gaposa hub."""
    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock:
        instance = AsyncMock()
        instance.send_command = AsyncMock(return_value="OK")
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_setup_entry():
    """Mock the setup entry."""
    with patch(
        "custom_components.gaposa_linkit.async_setup_entry", new_callable=AsyncMock
    ) as mock:
        mock.return_value = True
        yield mock


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant):
    """Test the user step of the config flow."""
    from custom_components.gaposa_linkit.config_flow import (
        GaposaLinkItConfigFlow,
    )

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    # Test showing the form without user input
    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert CONF_HOST in result["data_schema"].schema
    assert CONF_PORT in result["data_schema"].schema


@pytest.mark.asyncio
async def test_config_flow_user_step_with_input(hass: HomeAssistant):
    """Test the user step with valid input."""
    from custom_components.gaposa_linkit.config_flow import (
        GaposaLinkItConfigFlow,
    )

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        "channels": ["1", "2", "3"],
    }

    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == "create_entry"
    assert result["title"] == "Gaposa LinkIt (192.168.1.100)"
    assert result["data"] == user_input


@pytest.mark.asyncio
async def test_config_flow_user_step_with_default_port(hass: HomeAssistant):
    """Test the user step with default port."""
    from custom_components.gaposa_linkit.config_flow import (
        GaposaLinkItConfigFlow,
    )

    flow = GaposaLinkItConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.100",
        "channels": [],
    }

    result = await flow.async_step_user(user_input=user_input)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "192.168.1.100"


@pytest.mark.asyncio
async def test_options_flow_init(hass: HomeAssistant):
    """Test the init step of the options flow."""
    from custom_components.gaposa_linkit.config_flow import (
        GaposaLinkItOptionsFlowHandler,
    )

    flow = GaposaLinkItOptionsFlowHandler()
    flow.hass = hass

    # Mock the config_entry
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        "channels": ["1", "2"],
    }
    flow.config_entry = mock_config_entry

    result = await flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_init_with_input(hass: HomeAssistant):
    """Test the init step with input."""
    from custom_components.gaposa_linkit.config_flow import (
        GaposaLinkItOptionsFlowHandler,
    )

    flow = GaposaLinkItOptionsFlowHandler()
    flow.hass = hass

    # Mock the config_entry
    mock_config_entry = MagicMock()
    mock_config_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        "channels": ["1", "2"],
    }
    flow.config_entry = mock_config_entry

    # Mock the async_update_entry method
    hass.config_entries.async_update_entry = MagicMock()

    user_input = {
        CONF_HOST: "192.168.1.101",
        CONF_PORT: 5000,
        "channels": ["1", "2", "3"],
    }

    result = await flow.async_step_init(user_input=user_input)
    assert result["type"] == "create_entry"
