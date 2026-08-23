"""pytest configuration and fixtures."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

# Add the custom_components directory to the path
custom_components_path = Path(__file__).parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))


@pytest.fixture
async def hass(tmp_path: Path):
    """Provide a Home Assistant instance for testing."""
    hass = HomeAssistant(str(tmp_path))
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock(return_value=True)
    hass.config_entries.async_update_entry = MagicMock()
    return hass
