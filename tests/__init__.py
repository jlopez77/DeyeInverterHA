import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.deye_inverter import async_setup_entry, async_unload_entry
from custom_components.deye_inverter.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test setup of the integration entry."""
    mock_entry = MagicMock()
    mock_entry.data = {
        "host": "192.168.1.100",
        "port": 8899,
        "serial": "ABC123",
        "installed_power": 5000,
    }
    mock_entry.entry_id = "test_entry"

    hass = MagicMock()
    hass.data = {}

    with patch(
        "custom_components.deye_inverter.DeyeDataUpdateCoordinator"
    ) as mock_coordinator_class, patch(
        "custom_components.deye_inverter.async_forward_entry_setups", new=AsyncMock()
    ) as mock_forward:
        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, mock_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert "test_entry" in hass.data[DOMAIN]
        mock_coordinator.async_config_entry_first_refresh.assert_awaited_once()
        mock_forward.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_unload_entry():
    """Test unloading of the integration entry."""
    hass = MagicMock()
    entry_id = "test_entry"
    hass.data = {
        DOMAIN: {entry_id: "coordinator_mock"}
    }

    mock_entry = MagicMock()
    mock_entry.entry_id = entry_id

    with patch(
        "custom_components.deye_inverter.config_entries.async_unload_platforms", new=AsyncMock(return_value=True)
    ) as mock_unload:
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        assert entry_id not in hass.data[DOMAIN]
        mock_unload.assert_awaited_once()
