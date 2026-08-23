"""Tests for constants and configuration."""
from custom_components.gaposa_linkit.const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_HOST,
    CONF_PORT,
    CMD_UP,
    CMD_DOWN,
    CMD_STOP,
    CMD_PAIR,
    CMD_UNPAIR,
)


def test_domain_constant():
    """Test DOMAIN constant."""
    assert DOMAIN == "gaposa_linkit"


def test_default_port_constant():
    """Test DEFAULT_PORT constant."""
    assert DEFAULT_PORT == 4999


def test_conf_host_constant():
    """Test CONF_HOST constant."""
    assert CONF_HOST == "host"


def test_conf_port_constant():
    """Test CONF_PORT constant."""
    assert CONF_PORT == "port"


def test_command_constants():
    """Test command byte constants."""
    assert CMD_UP == 0xdd
    assert CMD_DOWN == 0xee
    assert CMD_STOP == 0xcc
    assert CMD_PAIR == 0xaa
    assert CMD_UNPAIR == 0xab


def test_command_uniqueness():
    """Test that all command constants are unique."""
    commands = [CMD_UP, CMD_DOWN, CMD_STOP, CMD_PAIR, CMD_UNPAIR]
    assert len(commands) == len(set(commands))
