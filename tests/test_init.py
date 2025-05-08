import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.deye_inverter import (
    async_setup_entry,
    async_unload_entry,
    async_setup,
)
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
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch(
        "custom_components.deye_inverter.coordinator.DeyeDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, mock_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert "test_entry" in hass.data[DOMAIN]
        mock_coordinator.async_config_entry_first_refresh.assert_awaited_once()
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(mock_entry, ["sensor"])


@pytest.mark.asyncio
async def test_async_unload_entry():
    """Test unloading of the integration entry."""
    hass = MagicMock()
    entry_id = "test_entry"
    hass.data = {DOMAIN: {entry_id: "coordinator_mock"}}

    mock_entry = MagicMock()
    mock_entry.entry_id = entry_id

    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, mock_entry)

    assert result is True
    assert entry_id not in hass.data[DOMAIN]
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(mock_entry, ["sensor"])

@pytest.mark.asyncio
async def test_async_setup_import_creates_flow():
    """Test YAML import triggers config flow init."""
    hass = MagicMock()
    hass.config_entries.flow.async_init = AsyncMock()

    # Run coroutines immediately on the event loop
    hass.async_create_task = lambda coro: asyncio.create_task(coro)

    config = {
        DOMAIN: {
            "host": "1.2.3.4",
            "port": 8899,
            "serial": "XYZ123",
            "installed_power": 4500,
        }
    }

    result = await async_setup(hass, config)

    assert result is True
    hass.config_entries.flow.async_init.assert_awaited_once_with(
        DOMAIN,
        context={"source": "import"},
        data=config[DOMAIN],
    )
