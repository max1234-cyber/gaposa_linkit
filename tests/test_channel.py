"""Tests for shared channel helpers."""

from custom_components.gaposa_linkit.channel import channel_bank_address
from custom_components.gaposa_linkit.channel import channel_enable_set_position
from custom_components.gaposa_linkit.channel import update_channel_entry_data
from custom_components.gaposa_linkit.const import CONF_CHANNELS
from custom_components.gaposa_linkit.const import CONF_ENABLE_SET_POSITION
from custom_components.gaposa_linkit.const import CONF_HOST
from custom_components.gaposa_linkit.const import CONF_PORT
from custom_components.gaposa_linkit.const import CONF_TRAVEL_TIMES
from custom_components.gaposa_linkit.const import DEFAULT_TRAVEL_TIME


def test_channel_bank_address():
    """Test bank and channel mapping."""
    assert channel_bank_address(1) == (0x00, 1)
    assert channel_bank_address(8) == (0x00, 8)
    assert channel_bank_address(9) == (0x01, 1)
    assert channel_bank_address(16) == (0x01, 8)
    assert channel_bank_address(17) == (0x02, 1)
    assert channel_bank_address(24) == (0x02, 8)


def test_channel_enable_set_position_supports_bool_and_mapping():
    """Test per-channel enable-set-position normalization."""
    assert channel_enable_set_position(True, "1") is True
    assert channel_enable_set_position(False, "1") is False
    assert channel_enable_set_position({"1": False, "2": True}, "1") is False
    assert channel_enable_set_position({"1": False, "2": True}, "2") is True


def test_update_channel_entry_data_updates_single_channel():
    """Test config-entry updates for per-channel helper entities."""
    entry_data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 4999,
        CONF_CHANNELS: ["1", "2"],
        CONF_ENABLE_SET_POSITION: True,
        CONF_TRAVEL_TIMES: {"1": 30},
    }

    updated_data = update_channel_entry_data(
        entry_data,
        "2",
        enable_set_position=False,
        travel_time=45,
    )

    assert updated_data[CONF_HOST] == "192.168.1.100"
    assert updated_data[CONF_PORT] == 4999
    assert updated_data[CONF_ENABLE_SET_POSITION] == {"1": True, "2": False}
    assert updated_data[CONF_TRAVEL_TIMES] == {"1": 30, "2": 45}


def test_update_channel_entry_data_preserves_defaults_for_other_channels():
    """Test default travel times are retained for selected channels."""
    updated_data = update_channel_entry_data(
        {
            CONF_CHANNELS: ["1", "2"],
            CONF_ENABLE_SET_POSITION: {"1": True, "2": True},
            CONF_TRAVEL_TIMES: {},
        },
        "1",
        enable_set_position=False,
    )

    assert updated_data[CONF_ENABLE_SET_POSITION] == {"1": False, "2": True}
    assert updated_data[CONF_TRAVEL_TIMES] == {
        "1": DEFAULT_TRAVEL_TIME,
        "2": DEFAULT_TRAVEL_TIME,
    }
