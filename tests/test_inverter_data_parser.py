import pytest
from custom_components.deye_inverter.InverterDataParser import (
    combine_registers,
    parse_raw,
    parse_battery_status,
    parse_grid_status,
    parse_smartload_status,
)

def test_combine_registers_unsigned():
    # Combine 2 registers: 0x1234 and 0x5678
    val = combine_registers([0x1234, 0x5678], signed=False)
    assert val == 0x12345678

def test_combine_registers_signed_negative():
    # 0xFFFF and 0xFFFE as signed = -2
    val = combine_registers([0xFFFF, 0xFFFE], signed=True)
    assert val < 0  # Confirm it's negative

def test_parse_battery_status():
    assert parse_battery_status(5) == "Discharge"
    assert parse_battery_status(-3) == "Charge"
    assert parse_battery_status(0) == "Stand-by"

def test_parse_grid_status():
    assert parse_grid_status(1) == "BUY"
    assert parse_grid_status(-1) == "SELL"
    assert parse_grid_status(0) == "Stand-by"

def test_parse_smartload_status():
    assert parse_smartload_status(1) == "ON"
    assert parse_smartload_status(0) == "OFF"
    assert parse_smartload_status(99) == "Unknown (99)"

def test_parse_raw_with_empty():
    # Should handle empty input gracefully
    result = parse_raw([])
    assert isinstance(result, dict)
    assert result == {}
