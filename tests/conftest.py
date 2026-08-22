"""pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add the custom_components directory to the path
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def hass():
    """Provide a Home Assistant instance for testing."""
    hass = HomeAssistant()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock(return_value=True)
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_async_setup():
    """Mock async setup component."""
    with pytest.mock.patch(
        "homeassistant.setup.async_setup_component", new_callable=AsyncMock
    ) as mock:
        mock.return_value = True
        yield mock
