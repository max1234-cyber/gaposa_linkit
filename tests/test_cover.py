"""Tests for the Gaposa cover platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.components.cover import CoverEntityFeature

from custom_components.gaposa_linkit.const import CMD_UP, CMD_DOWN, CMD_STOP


@pytest.fixture
async def mock_hub():
    """Create a mock hub."""
    hub = AsyncMock()
    hub.send_command = AsyncMock(return_value="OK")
    return hub


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
    return entry


@pytest.mark.asyncio
async def test_cover_initialization(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover entity initialization."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    
    assert cover._hub == mock_hub
    assert cover._bank == 0x00
    assert cover._bank_channel == 1
    assert cover._attr_unique_id == "test_entry_id_channel_1"
    assert cover._attr_name == "Gaposa Shade Channel 1"
    assert cover._attr_is_closed is None


@pytest.mark.asyncio
async def test_cover_supported_features(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover supported features."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    
    assert cover._attr_supported_features == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )


@pytest.mark.asyncio
async def test_cover_open(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test opening the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()
    
    mock_hub.send_command.assert_called_once_with(0x00, 1, CMD_UP)
    assert cover._attr_is_closed is False
    cover.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_cover_close(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test closing the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover.async_write_ha_state = MagicMock()

    await cover.async_close_cover()
    
    mock_hub.send_command.assert_called_once_with(0x00, 1, CMD_DOWN)
    assert cover._attr_is_closed is True
    cover.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_cover_stop(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test stopping the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover.async_write_ha_state = MagicMock()

    await cover.async_stop_cover()
    
    mock_hub.send_command.assert_called_once_with(0x00, 1, CMD_STOP)
    assert cover._attr_is_closed is False
    cover.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_cover_extra_state_attributes(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test extra state attributes."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover._last_hub_reply = "Test Reply"
    
    attributes = cover.extra_state_attributes
    assert attributes["last_hub_reply"] == "Test Reply"


@pytest.mark.asyncio
async def test_cover_open_with_reply(hass: HomeAssistant, mock_config_entry):
    """Test opening cover with hub reply."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    mock_hub = AsyncMock()
    mock_hub.send_command = AsyncMock(return_value="SUCCESS")
    
    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()
    
    assert cover._last_hub_reply == "SUCCESS"


@pytest.mark.asyncio
async def test_cover_channel_bank_mapping():
    """Test channel to bank mapping."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    mock_hub = AsyncMock()

    # Channels 1-8 should be bank 0x00
    cover1 = GaposaCover(mock_hub, "test", 1, 0x00, 1)
    assert cover1._bank == 0x00
    assert cover1._bank_channel == 1

    # Channels 9-16 should be bank 0x01
    cover9 = GaposaCover(mock_hub, "test", 9, 0x01, 1)
    assert cover9._bank == 0x01
    assert cover9._bank_channel == 1

    # Channels 17-24 should be bank 0x02
    cover17 = GaposaCover(mock_hub, "test", 17, 0x02, 1)
    assert cover17._bank == 0x02
    assert cover17._bank_channel == 1


@pytest.mark.asyncio
async def test_cover_added_to_hass(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover when added to hass."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1)
    cover.async_write_ha_state = MagicMock()
    cover.hass = hass

    # Simulate added to hass
    await cover.async_added_to_hass()
    
    # Should default to closed state
    assert cover._attr_is_closed is True
    cover.async_write_ha_state.assert_called_once()
