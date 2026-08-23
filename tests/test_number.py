"""Tests for per-channel number entities."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES
from custom_components.gaposa_linkit.const import get_config_update_signal


@pytest.mark.asyncio
async def test_travel_time_number_updates_config_entry(hass: HomeAssistant):
    """Test the travel-time entity persists updates."""
    from custom_components.gaposa_linkit.number import GaposaTravelTimeNumber

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        "channels": ["1"],
        "enable_set_position": {"1": True},
        "travel_times": {"1": 30},
    }
    entity = GaposaTravelTimeNumber(
        config_entry,
        1,
        30,
        get_config_update_signal(config_entry.entry_id),
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity.async_set_native_value(45)

    assert entity.native_value == 45
    assert entity.entity_category is EntityCategory.CONFIG
    assert entity.native_unit_of_measurement is UnitOfTime.SECONDS
    hass.config_entries.async_update_entry.assert_called_once()
    assert hass.config_entries.async_update_entry.call_args.kwargs["data"][CONF_TRAVEL_TIMES] == {
        "1": 45
    }


@pytest.mark.asyncio
async def test_travel_time_number_reacts_to_dispatcher_updates(hass: HomeAssistant):
    """Test the travel-time entity refreshes after config updates."""
    from custom_components.gaposa_linkit.number import GaposaTravelTimeNumber

    entity = GaposaTravelTimeNumber(
        MagicMock(entry_id="test_entry_id", data={}),
        1,
        30,
        get_config_update_signal("test_entry_id"),
    )
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()

    await entity.async_added_to_hass()

    async_dispatcher_send(
        hass,
        get_config_update_signal("test_entry_id"),
        {CONF_TRAVEL_TIMES: {"1": 90}},
    )

    assert entity.native_value == 90
