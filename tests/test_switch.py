"""Tests for per-channel switch entities."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.gaposa_linkit.const import CONF_ENABLE_SET_POSITION
from custom_components.gaposa_linkit.const import get_config_update_signal


@pytest.mark.asyncio
async def test_allow_set_position_switch_updates_config_entry(hass: HomeAssistant):
    """Test the allow-set-position entity persists updates."""
    from custom_components.gaposa_linkit.switch import GaposaAllowSetPositionSwitch

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "channels": ["1"],
        "enable_set_position": {"1": True},
        "travel_times": {"1": 30},
    }
    entity = GaposaAllowSetPositionSwitch(
        config_entry,
        1,
        True,
        get_config_update_signal(config_entry.entry_id),
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity.async_turn_off()

    assert entity.is_on is False
    assert entity.entity_category is EntityCategory.CONFIG
    hass.config_entries.async_update_entry.assert_called_once()
    assert hass.config_entries.async_update_entry.call_args.kwargs["data"][
        CONF_ENABLE_SET_POSITION
    ] == {"1": False}


@pytest.mark.asyncio
async def test_allow_set_position_switch_reacts_to_dispatcher_updates(
    hass: HomeAssistant,
):
    """Test the switch entity refreshes after config updates."""
    from custom_components.gaposa_linkit.switch import GaposaAllowSetPositionSwitch

    entity = GaposaAllowSetPositionSwitch(
        MagicMock(entry_id="test_entry_id", data={}),
        1,
        True,
        get_config_update_signal("test_entry_id"),
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity.async_added_to_hass()

    async_dispatcher_send(
        hass,
        get_config_update_signal("test_entry_id"),
        {CONF_ENABLE_SET_POSITION: {"1": False}},
    )

    assert entity.is_on is False
