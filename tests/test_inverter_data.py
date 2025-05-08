import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from custom_components.deye_inverter.InverterData import InverterData
from custom_components.deye_inverter.const import DOMAIN
from custom_components.deye_inverter.InverterData import ModbusException


@pytest.fixture(autouse=True)
def patch_pysolarmanv5():
    with patch("custom_components.deye_inverter.InverterData.PySolarmanV5") as mock_class:
        mock_instance = MagicMock()
        mock_instance.read_holding_registers = MagicMock()
        mock_class.return_value = mock_instance
        yield


@pytest.mark.asyncio
async def test_trigger_reload_after_max_errors():
    """Test that integration reload is triggered after max consecutive read errors."""
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

    inverter._modbus.read_holding_registers.side_effect = RuntimeError("Mock failure")

    for _ in range(5):
        with pytest.raises(Exception):
            await inverter.fetch_data()

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

    inverter._modbus.read_holding_registers.side_effect = RuntimeError("Mock failure")

    for _ in range(3):  # fewer than max_errors
        with pytest.raises(Exception):
            await inverter.fetch_data()

    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_data_logs_error_and_raises(caplog):
    """Test that fetch_data logs the error and raises ModbusException."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._modbus.read_holding_registers = MagicMock(side_effect=RuntimeError("Test failure"))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ModbusException):
            await inverter.fetch_data()

    assert "Error reading registers: Test failure" in caplog.text


@pytest.mark.asyncio
async def test_fetch_data_success_returns_parsed():
    """Test that fetch_data returns parsed result correctly."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._modbus.read_holding_registers = MagicMock(return_value=[0] * 100)

    result = await inverter.fetch_data()
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_fetch_data_without_hass_or_entry():
    """Ensure fetch_data works standalone without hass/config_entry (no reload logic)."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._modbus.read_holding_registers = MagicMock(return_value=[0] * 100)

    result = await inverter.fetch_data()
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_fetch_data_success_no_reload_trigger():
    """Ensure fetch_data does NOT trigger reload when no exception occurs."""
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
    inverter._modbus.read_holding_registers = MagicMock(return_value=[0] * 100)

    result = await inverter.fetch_data()

    assert isinstance(result, dict)
    hass.services.async_call.assert_not_called()
