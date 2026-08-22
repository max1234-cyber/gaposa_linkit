"""Tests for the Gaposa LinkIt integration setup."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.gaposa_linkit.const import DOMAIN, DEFAULT_PORT


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
    entry.add_update_listener = AsyncMock()
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test async setup entry."""
    from custom_components.gaposa_linkit import async_setup_entry

    mock_config_entry.add_update_listener = AsyncMock()

    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock_hub_class:
        mock_hub = AsyncMock()
        mock_hub_class.return_value = mock_hub

        # Mock async_forward_entry_setups
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        mock_hub_class.assert_called_once_with("192.168.1.100", 4999)
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            mock_config_entry, ["cover"]
        )


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
        mock_config_entry, ["cover"]
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
        mock_config_entry.add_update_listener = AsyncMock()

        await async_setup_entry(hass, mock_config_entry)

        # Verify hub is stored
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][mock_config_entry.entry_id] == mock_hub


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
    mock_entry.add_update_listener = AsyncMock()

    with patch("custom_components.gaposa_linkit.GaposaLinkItHub") as mock_hub_class:
        mock_hub = AsyncMock()
        mock_hub_class.return_value = mock_hub

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        await async_setup_entry(hass, mock_entry)

        # Verify correct host and port were passed
        mock_hub_class.assert_called_once_with("192.168.1.50", 5555)
