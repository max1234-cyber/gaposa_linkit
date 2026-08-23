"""Tests for the Gaposa cover platform."""
import asyncio
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

import pytest
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.gaposa_linkit.const import CMD_DOWN
from custom_components.gaposa_linkit.const import CMD_STOP
from custom_components.gaposa_linkit.const import CMD_UP
from custom_components.gaposa_linkit.const import CONF_ENABLE_SET_POSITION
from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES
from custom_components.gaposa_linkit.const import get_config_update_signal


@pytest.fixture
async def mock_hub():
    """Create a mock hub."""
    hub = AsyncMock()
    hub.send_command = AsyncMock(return_value="OK")
    return hub


def _make_cover(
    mock_hub,
    *,
    travel_time: int = 60,
    enable_set_position: bool = True,
):
    from custom_components.gaposa_linkit.cover import GaposaCover

    return GaposaCover(
        mock_hub,
        MagicMock(entry_id="test_entry_id", data={}),
        "test_entry_id",
        1,
        0x00,
        1,
        travel_time=travel_time,
        enable_set_position=enable_set_position,
    )


async def _drain_background_tasks():
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_cover_initialization(mock_hub):
    """Test cover entity initialization."""
    cover = _make_cover(mock_hub)

    assert cover._hub == mock_hub
    assert cover._bank == 0x00
    assert cover._bank_channel == 1
    assert cover._attr_unique_id == "test_entry_id_channel_1"
    assert cover._attr_name == "Shade"
    assert cover._attr_is_closed is None
    assert cover.current_cover_position == 0
    assert cover.device_info["name"] == "Channel 1"


@pytest.mark.asyncio
async def test_cover_supported_features_toggle(mock_hub):
    """Test cover supported features."""
    cover = _make_cover(mock_hub)
    assert cover.supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    disabled_cover = _make_cover(mock_hub, enable_set_position=False)
    assert disabled_cover.supported_features == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )


@pytest.mark.asyncio
async def test_cover_open_close_and_stop_commands(mock_hub):
    """Test opening, closing, and stopping the cover."""
    cover = _make_cover(mock_hub)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()
    await cover.async_stop_cover()
    await cover.async_close_cover()

    mock_hub.send_command.assert_has_calls(
        [
            call(0x00, 1, CMD_UP),
            call(0x00, 1, CMD_STOP),
            call(0x00, 1, CMD_DOWN),
        ]
    )
    assert cover.is_closing is True
    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_stop_freezes_intermediate_position(mock_hub):
    """Test stopping the cover at its current calculated position."""
    clock = {"now": 0.0}

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ):
        cover = _make_cover(mock_hub, travel_time=60)
        cover.async_write_ha_state = MagicMock()

        await cover.async_open_cover()
        clock["now"] = 30.0
        await cover.async_stop_cover()

    assert cover.current_cover_position == 50
    assert cover.is_opening is False
    assert cover.is_closing is False
    assert cover._attr_is_closed is False


@pytest.mark.asyncio
async def test_cover_background_timer_updates_during_motion(mock_hub):
    """Test periodic position updates while the cover is moving."""
    clock = {"now": 0.0}
    sleep_calls: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float):
        sleep_calls.append(delay)
        clock["now"] += delay
        await real_sleep(0)

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ), patch("custom_components.gaposa_linkit.cover.sleep", new=fake_sleep):
        cover = _make_cover(mock_hub, travel_time=2)
        cover.async_write_ha_state = MagicMock()

        await cover.async_open_cover()
        motion_task = cover._motion_task
        await _drain_background_tasks()
        if motion_task is not None:
            await motion_task

    assert sleep_calls == [1.0, 1.0]
    assert cover.current_cover_position == 100
    assert cover.is_opening is False
    assert cover.async_write_ha_state.call_count >= 3


@pytest.mark.asyncio
async def test_cover_set_position_auto_stops_when_enabled(mock_hub):
    """Test set position issues an automatic stop at the requested position."""
    clock = {"now": 0.0}
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float):
        clock["now"] += delay
        await real_sleep(0)

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ), patch("custom_components.gaposa_linkit.cover.sleep", new=fake_sleep):
        cover = _make_cover(mock_hub, travel_time=4)
        cover.async_write_ha_state = MagicMock()

        await cover.async_set_cover_position(position=50)
        motion_task = cover._motion_task
        await _drain_background_tasks()
        if motion_task is not None:
            await motion_task

    mock_hub.send_command.assert_has_calls(
        [
            call(0x00, 1, CMD_UP),
            call(0x00, 1, CMD_STOP),
        ]
    )
    assert cover.current_cover_position == 50
    assert cover.is_opening is False


@pytest.mark.asyncio
async def test_cover_set_position_to_endpoint_does_not_auto_stop(mock_hub):
    """Test set position to 0/100 uses full-travel behavior without auto-stop."""
    clock = {"now": 0.0}

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ):
        cover = _make_cover(mock_hub, travel_time=4)
        cover.async_write_ha_state = MagicMock()

        await cover.async_set_cover_position(position=100)
        clock["now"] = 3.0
        await cover.async_set_cover_position(position=0)

    mock_hub.send_command.assert_has_calls(
        [
            call(0x00, 1, CMD_UP),
            call(0x00, 1, CMD_DOWN),
        ]
    )
    assert call(0x00, 1, CMD_STOP) not in mock_hub.send_command.call_args_list


@pytest.mark.asyncio
async def test_cover_set_position_starts_motion_when_feature_disabled(mock_hub):
    """Test set position still starts directional motion when set-position is disabled."""
    clock = {"now": 0.0}

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ):
        cover = _make_cover(mock_hub, travel_time=4, enable_set_position=False)
        cover.async_write_ha_state = MagicMock()

        await cover.async_set_cover_position(position=80)
        clock["now"] = 3.0
        await cover.async_set_cover_position(position=20)

    mock_hub.send_command.assert_has_calls(
        [
            call(0x00, 1, CMD_UP),
            call(0x00, 1, CMD_DOWN),
        ]
    )
    assert call(0x00, 1, CMD_STOP) not in mock_hub.send_command.call_args_list


@pytest.mark.asyncio
async def test_cover_multiple_commands_in_quick_succession(mock_hub):
    """Test a new command recalculates motion from the current position."""
    clock = {"now": 0.0}

    with patch(
        "custom_components.gaposa_linkit.cover.monotonic",
        side_effect=lambda: clock["now"],
    ):
        cover = _make_cover(mock_hub, travel_time=2)
        cover.async_write_ha_state = MagicMock()

        await cover.async_open_cover()
        clock["now"] = 1.0
        await cover.async_close_cover()

        assert cover.current_cover_position == 50
        assert cover.is_closing is True
        await cover.async_will_remove_from_hass()

    mock_hub.send_command.assert_has_calls(
        [
            call(0x00, 1, CMD_UP),
            call(0x00, 1, CMD_DOWN),
        ]
    )


@pytest.mark.asyncio
async def test_cover_config_update_changes_travel_time_and_features(
    hass: HomeAssistant, mock_hub
):
    """Test config updates are applied in-place without recreating the entity."""
    cover = _make_cover(mock_hub, travel_time=60)
    cover.hass = hass
    cover.async_write_ha_state = MagicMock()

    await cover.async_added_to_hass()

    async_dispatcher_send(
        hass,
        get_config_update_signal("test_entry_id"),
        {
            CONF_ENABLE_SET_POSITION: {"1": False},
            CONF_TRAVEL_TIMES: {"1": 120},
        },
    )

    assert cover._travel_time == 120
    assert cover.supported_features == (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    await cover.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_cover_added_to_hass_defaults_closed(
    hass: HomeAssistant, mock_hub
):
    """Test cover defaults to closed when added to hass."""
    cover = _make_cover(mock_hub)
    cover.hass = hass
    cover.async_write_ha_state = MagicMock()

    await cover.async_added_to_hass()

    assert cover._attr_is_closed is True
    cover.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_cover_timer_cleanup_on_entity_unload(mock_hub):
    """Test the background timer is cancelled when the entity is removed."""
    cover = _make_cover(mock_hub, travel_time=60)
    cover.async_write_ha_state = MagicMock()

    await cover.async_open_cover()

    motion_task = cover._motion_task
    assert motion_task is not None

    await cover.async_will_remove_from_hass()

    assert cover._motion_task is None
    assert motion_task.cancelled() or motion_task.done()
