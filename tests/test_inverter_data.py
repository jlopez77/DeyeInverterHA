import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.deye_inverter.InverterData import InverterData

@pytest.mark.asyncio
async def test_trigger_reload_after_max_errors():
    """Test that integration reload is triggered after max consecutive read errors."""
    # Setup mocked hass and config_entry
    hass = MagicMock()
    hass.services.async_call = AsyncMock()

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    # Instantiate InverterData with mocks
    inverter = InverterData(
        host="localhost",
        port=8899,
        serial="1",
        hass=hass,
        config_entry=config_entry,
    )

    # Simulate read_holding_registers always failing
    inverter._modbus.read_holding_registers = MagicMock(side_effect=RuntimeError("Mock failure"))

    # Attempt 5 reads to exceed the max error threshold (which is 5)
    for i in range(5):
        with pytest.raises(Exception):
            await inverter.fetch_data()

    # Check that reload was triggered
    hass.services.async_call.assert_called_once_with(
        "homeassistant",
        "reload_config_entry",
        {"entry_id": "test_entry"},
        blocking=False,
    )

@pytest.mark.asyncio
async def test_no_reload_before_threshold():
    """Ensure reload is not triggered before reaching the threshold."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    inverter = InverterData(
        host="localhost",
        port=8899,
        serial="1",
        hass=hass,
        config_entry=config_entry,
    )

    inverter._modbus.read_holding_registers = MagicMock(side_effect=RuntimeError("Mock failure"))

    # Only 3 failures (below the threshold)
    for i in range(3):
        with pytest.raises(Exception):
            await inverter.fetch_data()

    hass.services.async_call.assert_not_called()
