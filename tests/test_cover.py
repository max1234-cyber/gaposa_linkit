"""Tests for the Gaposa cover platform."""
import asyncio
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

import pytest
from homeassistant.components.cover import ATTR_POSITION
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.gaposa_linkit.const import CMD_DOWN
from custom_components.gaposa_linkit.const import CMD_STOP
from custom_components.gaposa_linkit.const import CMD_UP
from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES


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
        CONF_TRAVEL_TIMES: {"1": 60, "2": 75, "3": 90},
    }
    return entry


@pytest.mark.asyncio
async def test_cover_initialization(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover entity initialization."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)

    assert cover._hub == mock_hub
    assert cover._bank == 0x00
    assert cover._bank_channel == 1
    assert cover._attr_unique_id == "test_entry_id_channel_1"
    assert cover._attr_name == "Gaposa Shade Channel 1"
    assert cover._attr_is_closed is True
    assert cover.current_cover_position == 0


@pytest.mark.asyncio
async def test_cover_supported_features(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover supported features."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)

    assert cover._attr_supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )


@pytest.mark.asyncio
async def test_cover_open(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test opening the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()

    mock_hub.send_command.assert_called_once_with(0x00, 1, CMD_UP)
    assert cover._attr_is_closed is False
    assert cover.is_opening is True
    cover.async_write_ha_state.assert_called_once()
    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_close(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test closing the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)
    cover.async_write_ha_state = MagicMock()
    cover._current_position = 100

    await cover.async_close_cover()

    mock_hub.send_command.assert_called_once_with(0x00, 1, CMD_DOWN)
    assert cover.is_closing is True
    cover.async_write_ha_state.assert_called_once()
    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_stop(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test stopping the cover."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=0.2)
    cover.async_write_ha_state = MagicMock()

    with patch("custom_components.gaposa_linkit.cover.POSITION_UPDATE_INTERVAL", 0.01):
        await cover.async_open_cover()
        await asyncio.sleep(0.05)
        await cover.async_stop_cover()

    assert mock_hub.send_command.call_args_list[1] == call(0x00, 1, CMD_STOP)
    assert 0 < cover.current_cover_position < 100
    assert cover.is_opening is False
    assert cover.is_closing is False
    assert cover._attr_is_closed is False


@pytest.mark.asyncio
async def test_cover_extra_state_attributes(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test extra state attributes."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)
    cover._attr_extra_state_attributes = {"last_hub_reply": "Test Reply"}

    attributes = cover.extra_state_attributes
    assert attributes["last_hub_reply"] == "Test Reply"


@pytest.mark.asyncio
async def test_cover_open_with_reply(hass: HomeAssistant, mock_config_entry):
    """Test opening cover with hub reply."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    mock_hub = AsyncMock()
    mock_hub.send_command = AsyncMock(return_value="SUCCESS")

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()

    assert cover._attr_extra_state_attributes["last_hub_reply"] == "SUCCESS"
    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_channel_bank_mapping():
    """Test channel to bank mapping."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    mock_hub = AsyncMock()

    # Channels 1-8 should be bank 0x00
    cover1 = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=60)
    assert cover1._bank == 0x00
    assert cover1._bank_channel == 1

    # Channels 9-16 should be bank 0x01
    cover9 = GaposaCover(mock_hub, "test", 9, 0x01, 1, travel_time=60)
    assert cover9._bank == 0x01
    assert cover9._bank_channel == 1

    # Channels 17-24 should be bank 0x02
    cover17 = GaposaCover(mock_hub, "test", 17, 0x02, 1, travel_time=60)
    assert cover17._bank == 0x02
    assert cover17._bank_channel == 1


@pytest.mark.asyncio
async def test_cover_added_to_hass(hass: HomeAssistant, mock_hub, mock_config_entry):
    """Test cover when added to hass."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, mock_config_entry.entry_id, 1, 0x00, 1, travel_time=60)
    cover.async_write_ha_state = MagicMock()
    cover.hass = hass

    # Simulate added to hass
    await cover.async_added_to_hass()

    # Should default to closed state
    assert cover._attr_is_closed is True
    cover.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_cover_current_position_intermediate(mock_hub):
    """Test optimistic position calculation for an in-flight opening motion."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=60)
    cover._motion_direction = "opening"
    cover._motion_started_at = 0.0
    cover._motion_start_position = 0.0
    cover._motion_target_position = 100.0
    cover._motion_duration = 60.0

    with patch("custom_components.gaposa_linkit.cover.monotonic", return_value=30.0):
        assert cover.current_cover_position == 50
        assert cover.is_opening is True
        assert cover.is_closing is False


@pytest.mark.asyncio
async def test_cover_set_position_sends_stop_at_target(mock_hub):
    """Test set_position uses elapsed travel time and sends a stop command."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=0.2)
    cover.async_write_ha_state = MagicMock()

    with patch("custom_components.gaposa_linkit.cover.POSITION_UPDATE_INTERVAL", 0.01):
        await cover.async_set_cover_position(**{ATTR_POSITION: 50})
        await asyncio.sleep(0.15)

    assert cover.current_cover_position == 50
    assert cover.is_opening is False
    mock_hub.send_command.assert_has_calls([call(0x00, 1, CMD_UP), call(0x00, 1, CMD_STOP)])


@pytest.mark.asyncio
async def test_cover_background_timer_updates_state(mock_hub):
    """Test the background task updates Home Assistant state while moving."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=0.2)
    cover.async_write_ha_state = MagicMock()

    with patch("custom_components.gaposa_linkit.cover.POSITION_UPDATE_INTERVAL", 0.01):
        await cover.async_open_cover()
        await asyncio.sleep(0.05)

    assert cover.async_write_ha_state.call_count >= 2
    assert cover.current_cover_position > 0
    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_multiple_commands_cancel_pending_auto_stop(mock_hub):
    """Test a new command cancels a pending auto-stop from set_position."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=0.2)
    cover.async_write_ha_state = MagicMock()

    with patch("custom_components.gaposa_linkit.cover.POSITION_UPDATE_INTERVAL", 0.01):
        await cover.async_set_cover_position(**{ATTR_POSITION: 50})
        await cover.async_open_cover()
        await asyncio.sleep(0.25)

    assert cover.current_cover_position == 100
    assert cover.is_opening is False
    assert mock_hub.send_command.call_args_list == [call(0x00, 1, CMD_UP), call(0x00, 1, CMD_UP)]


@pytest.mark.asyncio
async def test_cover_cleanup_cancels_motion_task(mock_hub):
    """Test entity unload cleans up the motion timer task."""
    from custom_components.gaposa_linkit.cover import GaposaCover

    cover = GaposaCover(mock_hub, "test", 1, 0x00, 1, travel_time=0.2)
    cover.async_write_ha_state = MagicMock()

    with patch("custom_components.gaposa_linkit.cover.POSITION_UPDATE_INTERVAL", 0.01):
        await cover.async_open_cover()
        task = cover._motion_task
        await cover.async_will_remove_from_hass()

    assert task is not None
    assert task.cancelled()
    assert cover._motion_task is None
