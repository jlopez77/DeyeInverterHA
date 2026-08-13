import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from custom_components.deye_inverter.InverterData import InverterData
from custom_components.deye_inverter.const import DOMAIN
from custom_components.deye_inverter.InverterData import ModbusReadError


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

    hass.config_entries.async_reload.assert_called_once_with("test_entry")
    hass.async_create_task.assert_called_once()


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

    hass.config_entries.async_reload.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_data_logs_error_and_raises(caplog):
    """Test that fetch_data logs the error and raises ModbusReadError."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._modbus.read_holding_registers = MagicMock(side_effect=RuntimeError("Test failure"))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ModbusReadError):
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
async def test_fetch_data_reads_optional_blocks():
    """All four blocks read fine: device-info metrics are parsed."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._modbus.read_holding_registers = MagicMock(
        side_effect=lambda register_addr, quantity: [1] * quantity
    )

    result = await inverter.fetch_data()

    assert "PV1 Power" in result
    assert "Inverter ID" in result
    assert "Communication Board Version No." in result


@pytest.mark.asyncio
async def test_fetch_data_optional_blocks_best_effort():
    """Optional block failures do not fail the update or count as errors."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    calls = {"n": 0}

    def read(register_addr, quantity):
        calls["n"] += 1
        if calls["n"] <= 2:  # core blocks succeed
            return [1] * quantity
        raise RuntimeError("unsupported block")

    inverter._modbus.read_holding_registers = MagicMock(side_effect=read)

    result = await inverter.fetch_data()

    assert "PV1 Power" in result
    assert "Inverter ID" not in result
    assert "Work Mode" not in result
    assert inverter._error_count == 0


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
    hass.config_entries.async_reload.assert_not_called()

@pytest.mark.asyncio
async def test_trigger_reload_logs_error_if_missing_parts(caplog):
    """Ensure reload logs an error and exits if hass or config_entry is missing."""
    inverter = InverterData(host="localhost", port=8899, serial="1")
    inverter._hass = None  # Explicitly missing
    inverter._config_entry = None

    with caplog.at_level(logging.ERROR):
        await inverter._trigger_reload()

    assert "Cannot reload: 'hass' or 'config_entry' is missing." in caplog.text


@pytest.mark.asyncio
async def test_fetch_data_applies_the_configured_variant():
    """The variant given to the client is applied to the parsed values."""
    from custom_components.deye_inverter.InverterDataParser import register_index

    def read(register_addr, quantity):
        regs = [0] * quantity
        if register_addr <= 0x00B2 <= register_addr + quantity - 1:
            regs[0x00B2 - register_addr] = 301  # Total Load Power
        return regs

    default = InverterData(host="localhost", port=8899, serial="1")
    default._modbus.read_holding_registers = MagicMock(side_effect=read)
    scaled = InverterData(host="localhost", port=8899, serial="1", mod=2)
    scaled._modbus.read_holding_registers = MagicMock(side_effect=read)

    assert register_index(0x00B2) is not None
    assert (await default.fetch_data())["Total Load Power"] == pytest.approx(301)
    assert (await scaled.fetch_data())["Total Load Power"] == pytest.approx(3010)
