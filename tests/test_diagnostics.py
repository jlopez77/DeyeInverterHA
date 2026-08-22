"""Tests for block-length validation and the diagnostics download."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.deye_inverter.const import (
    CORE_REGISTER_BLOCKS,
    DOMAIN,
    OPTIONAL_REGISTER_BLOCKS,
    REGISTER_BLOCKS,
)
from custom_components.deye_inverter.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.deye_inverter.InverterData import InverterData, ModbusReadError

RAW_LEN = sum(end - start + 1 for start, end in REGISTER_BLOCKS)


@pytest.fixture(autouse=True)
def patch_pysolarmanv5():
    """The client opens a socket in its constructor."""
    with patch(
        "custom_components.deye_inverter.InverterData.PySolarmanV5"
    ) as mock_class:
        mock_class.return_value = MagicMock()
        yield


def _inverter():
    inverter = InverterData(host="localhost", port=8899, serial="1", mod=2)
    inverter._modbus = MagicMock()
    return inverter


def _full_read(register_addr, quantity):
    return [0] * quantity


async def test_short_core_block_fails_the_read():
    """A truncated block would silently shift every later register."""
    inverter = _inverter()
    start = CORE_REGISTER_BLOCKS[0][0]
    inverter._modbus.read_holding_registers = MagicMock(
        side_effect=lambda register_addr, quantity: [0] * (quantity - 1)
    )

    with pytest.raises(ModbusReadError) as err:
        await inverter.fetch_data()

    assert f"0x{start:04X}" in str(err.value)
    assert "asked for" in str(err.value)


async def test_short_optional_block_is_padded_not_shifted():
    """Optional blocks stay best-effort, but must not misalign the list."""
    inverter = _inverter()
    optional_start = OPTIONAL_REGISTER_BLOCKS[0][0]

    def read(register_addr, quantity):
        if register_addr == optional_start:
            return [0] * (quantity - 2)
        return [0] * quantity

    inverter._modbus.read_holding_registers = MagicMock(side_effect=read)

    result = await inverter.fetch_data()

    assert len(inverter.last_raw) == RAW_LEN
    # Core metrics survive; the short optional block loses its own
    assert "PV1 Power" in result
    assert "Inverter ID" not in result
    assert inverter._error_count == 0


async def test_last_read_is_recorded_per_block():
    """Every block is reported, with the addresses it covers."""
    inverter = _inverter()
    inverter._modbus.read_holding_registers = MagicMock(side_effect=_full_read)

    await inverter.fetch_data()

    assert len(inverter.last_blocks) == len(REGISTER_BLOCKS)
    first = inverter.last_blocks[0]
    start, end = CORE_REGISTER_BLOCKS[0]
    assert first["range"] == f"0x{start:04X}-0x{end:04X}"
    assert first["expected"] == first["received"] == end - start + 1
    assert first["ok"] is True
    assert f"0x{start:04X}" in first["registers"]
    assert first["hex"].startswith("0000")


async def test_failed_block_is_reported_with_its_error():
    inverter = _inverter()
    optional_start = OPTIONAL_REGISTER_BLOCKS[0][0]

    def read(register_addr, quantity):
        if register_addr == optional_start:
            raise RuntimeError("illegal data address")
        return [0] * quantity

    inverter._modbus.read_holding_registers = MagicMock(side_effect=read)

    await inverter.fetch_data()

    failed = [b for b in inverter.last_blocks if not b["ok"]]
    assert len(failed) == 1
    assert failed[0]["error"] == "illegal data address"
    assert "registers" not in failed[0]


async def test_diagnostics_dump(hass):
    """The dump carries the raw blocks and the parsed values together."""
    inverter = _inverter()
    inverter._modbus.read_holding_registers = MagicMock(side_effect=_full_read)
    parsed = await inverter.fetch_data()

    coordinator = MagicMock()
    coordinator.inverter = inverter
    coordinator.mod = 2
    coordinator.data = {**parsed, "Inverter ID": "2602092548"}

    entry = MagicMock()
    entry.entry_id = "abc"
    entry.data = {
        "host": "192.168.3.49",
        "serial": "1131691043",
        "port": 8899,
        "mod": 2,
    }
    entry.options = {"mod": 2}
    hass.data[DOMAIN] = {"abc": coordinator}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["scaling_variant"] == 2
    assert result["last_read"]["register_count"] == RAW_LEN
    assert len(result["last_read"]["blocks"]) == len(REGISTER_BLOCKS)
    assert result["register_blocks"]["core"][0].startswith("0x")
    assert "PV1 Power" in result["parsed"]


async def test_diagnostics_redacts_the_installation_details(hass):
    """Host, serial and the device's own ID are of no use in a report."""
    coordinator = MagicMock()
    coordinator.inverter = None
    coordinator.mod = 0
    coordinator.data = {"Inverter ID": "2602092548", "PV1 Power": 1.0}

    entry = MagicMock()
    entry.entry_id = "abc"
    entry.data = {"host": "192.168.3.49", "serial": "1131691043", "port": 8899}
    entry.options = {}
    hass.data[DOMAIN] = {"abc": coordinator}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"]["host"] == "**REDACTED**"
    assert result["entry"]["data"]["serial"] == "**REDACTED**"
    assert result["entry"]["data"]["port"] == 8899
    assert result["parsed"]["Inverter ID"] == "**REDACTED**"
    assert result["parsed"]["PV1 Power"] == 1.0


async def test_diagnostics_before_the_first_read(hass):
    """An inverter that never answered still produces a usable dump."""
    entry = MagicMock()
    entry.entry_id = "missing"
    entry.data = {"host": "h", "serial": "s"}
    entry.options = {}
    hass.data[DOMAIN] = {}

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["last_read"] == {"register_count": 0, "blocks": []}
    assert result["parsed"] == {}
    assert result["scaling_variant"] is None
