import pytest
from unittest.mock import patch
from custom_components.deye_inverter.InverterDataParser import (
    combine_registers,
    parse_raw,
    parse_battery_status,
    parse_grid_status,
    parse_smartload_status,
)

# === LOW-LEVEL UNIT TESTS ===

def test_combine_registers_unsigned():
    val = combine_registers([0x1234, 0x5678], signed=False)
    assert val == 0x12345678

def test_combine_registers_signed_negative():
    val = combine_registers([0xFFFF, 0xFFFE], signed=True)
    assert val < 0

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
    result = parse_raw([])
    assert isinstance(result, dict)
    assert result == {}

# === ADVANCED PARSE_RAW TESTS ===

@pytest.mark.parametrize(
    "raw, expected",
    [
        # ASCII rule
        ([0x4142, 0x4300], {"Device Name": "ABC"}),
        # Battery Status
        ([0] * (0x00BE - 0x003B) + [5], {"Battery Status": "Discharge (5)"}),
        # Grid-connected Status
        ([0] * (0x00C2 - 0x003B) + [0], {"Grid-connected Status": "Off-Grid"}),
        # Bitfield rule
        ([0] * 20 + [0x00FF], {"Alarm Flags": 255}),
    ],
)
def test_parse_raw_various_cases(raw, expected, monkeypatch):
    fake_definitions = [
        {
            "section": "Test",
            "items": [
                {
                    "titleEN": "Device Name",
                    "parserRule": 5,
                    "registers": ["0x003B", "0x003C"],
                },
                {
                    "titleEN": "Battery Status",
                    "registers": ["0x00BE"],
                    "signed": True,
                },
                {
                    "titleEN": "Grid-connected Status",
                    "registers": ["0x00C2"],
                },
                {
                    "titleEN": "Alarm Flags",
                    "parserRule": 6,
                    "registers": ["0x004F"],
                },
            ],
        }
    ]
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_definitions
    )
    result = parse_raw(raw)
    for key, val in expected.items():
        assert result.get(key) == val
