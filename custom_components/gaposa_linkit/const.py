DOMAIN = "gaposa_linkit"
DEFAULT_PORT = 4999  # Standard iTach TCP port for serial
DEFAULT_TRAVEL_TIME = 60
CONF_HOST = "host"
CONF_PORT = "port"
CONF_CHANNELS = "channels"
CONF_ENABLE_SET_POSITION = "enable_set_position"
CONF_TRAVEL_TIMES = "travel_times"

# Command Bytes
CMD_UP = 0xdd
CMD_DOWN = 0xee
CMD_STOP = 0xcc
CMD_PAIR = 0xaa
CMD_UNPAIR = 0xab


def get_config_update_signal(entry_id: str) -> str:
    """Return the dispatcher signal for config updates."""
    return f"{DOMAIN}_{entry_id}_config_updated"
