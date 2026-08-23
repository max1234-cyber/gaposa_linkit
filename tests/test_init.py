"""Tests for the Gaposa LinkIt integration setup."""
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.gaposa_linkit.const import CONF_CHANNELS
from custom_components.gaposa_linkit.const import CONF_ENABLE_SET_POSITION
from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES
from custom_components.gaposa_linkit.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        "channels": ["1", "2", "3"],
    }
    entry.async_on_unload = MagicMock(return_value=MagicMock())
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test async setup entry."""
    from custom_components.gaposa_linkit import async_setup_entry

    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock_hub_class:
        mock_hub = AsyncMock()
        mock_hub_class.return_value = mock_hub

        # Mock async_forward_entry_setups
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        mock_hub_class.assert_called_once_with("192.168.1.100", 4999)
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            mock_config_entry, ["cover", "number", "switch"]
        )
        assert hass.data[DOMAIN][mock_config_entry.entry_id]["hub"] == mock_hub


@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant, mock_config_entry):
    """Test async unload entry."""
    from custom_components.gaposa_linkit import async_unload_entry

    # Setup mock data
    hass.data[DOMAIN] = {mock_config_entry.entry_id: "mock_hub"}

    # Mock async_unload_platforms
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once_with(
        mock_config_entry, ["cover", "number", "switch"]
    )
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_failure(hass: HomeAssistant, mock_config_entry):
    """Test async unload entry when platforms fail to unload."""
    from custom_components.gaposa_linkit import async_unload_entry

    # Setup mock data
    hass.data[DOMAIN] = {mock_config_entry.entry_id: "mock_hub"}

    # Mock async_unload_platforms to fail
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    # Data should NOT be removed when unload fails
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_update_listener(hass: HomeAssistant, mock_config_entry):
    """Test update listener for options flow."""
    from custom_components.gaposa_linkit import update_listener

    # Mock async_reload
    hass.config_entries.async_reload = AsyncMock(return_value=True)

    await update_listener(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_called_once_with(mock_config_entry.entry_id)


@pytest.mark.asyncio
async def test_update_listener_dispatches_cover_setting_changes(
    hass: HomeAssistant, mock_config_entry
):
    """Test cover-only setting changes update entities without a reload."""
    from custom_components.gaposa_linkit import update_listener

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "hub": "mock_hub",
            "entry_data": dict(mock_config_entry.data),
        }
    }
    hass.config_entries.async_reload = AsyncMock(return_value=True)

    updated_entry = MagicMock()
    updated_entry.entry_id = mock_config_entry.entry_id
    updated_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2", "3"],
        CONF_ENABLE_SET_POSITION: {"1": False, "2": True, "3": True},
        CONF_TRAVEL_TIMES: {"1": 30, "2": 45, "3": 60},
    }

    with patch("custom_components.gaposa_linkit.async_dispatcher_send") as mock_dispatch:
        await update_listener(hass, updated_entry)

    hass.config_entries.async_reload.assert_not_called()
    mock_dispatch.assert_called_once_with(
        hass,
        "gaposa_linkit_test_entry_id_config_updated",
        updated_entry.data,
    )
    assert hass.data[DOMAIN][mock_config_entry.entry_id]["entry_data"] == updated_entry.data


@pytest.mark.asyncio
async def test_setup_entry_stores_hub_in_hass_data(hass: HomeAssistant, mock_config_entry):
    """Test that setup stores hub in hass.data."""
    from custom_components.gaposa_linkit import async_setup_entry

    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock_hub_class:
        mock_hub = AsyncMock()
        mock_hub_class.return_value = mock_hub

        # Initialize hass.data
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # Mock async_forward_entry_setups
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
        await async_setup_entry(hass, mock_config_entry)

        # Verify hub is stored
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][mock_config_entry.entry_id]["hub"] == mock_hub


@pytest.mark.asyncio
async def test_setup_entry_with_custom_port(hass: HomeAssistant):
    """Test setup entry with custom port."""
    from custom_components.gaposa_linkit import async_setup_entry

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_id"
    mock_entry.data = {
        CONF_HOST: "192.168.1.50",
        CONF_PORT: 5555,
        "channels": ["1"],
    }
    mock_entry.add_update_listener = MagicMock(return_value=MagicMock())
    mock_entry.async_on_unload = MagicMock(return_value=MagicMock())

    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock_hub_class:
        mock_hub = AsyncMock()
        mock_hub_class.return_value = mock_hub

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        await async_setup_entry(hass, mock_entry)

        # Verify correct host and port were passed
        mock_hub_class.assert_called_once_with("192.168.1.50", 5555)
