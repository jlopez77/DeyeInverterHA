import pytest
import json
from unittest.mock import mock_open, patch
from custom_components.deye_inverter.InverterDataParser import (
    _load_definitions,
    parse_raw,
    combine_registers,
)


def test_load_definitions_json_error():
    bad_json = "{bad: json"  # Invalid JSON
    with patch("importlib.resources.read_text", return_value=bad_json):
        result = _load_definitions()
        assert result == {}  # Should fallback to empty dict


def test_load_definitions_fallback_file():
    # Simulate importlib.resources failure and fallback file with good content
    fallback_json = json.dumps({"section": {"items": []}})
    with patch("importlib.resources.read_text", side_effect=Exception()), \
         patch("pathlib.Path.read_text", return_value=fallback_json):
        result = _load_definitions()
        assert "section" in result


def test_combine_registers_reverse():
    # Test reverse logic: will reverse and combine [0x0001, 0x0002] => 0x00020001
    value = combine_registers([0x0001, 0x0002], signed=False, reverse=True)
    assert value == 0x00020001


def test_parse_raw_ascii_control_char(monkeypatch):
    # Test parserRule 5 with non-printable characters → returns hex string
    fake_defs = [
        {
            "section": "ASCII",
            "items": [
                {
                    "titleEN": "Serial",
                    "registers": ["0x003B"],
                    "parserRule": 5,
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)

    result = parse_raw([0x0001])  # High byte 0x00, low byte 0x01
    assert result["Serial"].startswith("0x")


def test_parse_raw_battery_status_positive(monkeypatch):
    fake_defs = [
        {
            "section": "Battery",
            "items": [
                {
                    "titleEN": "Battery Status",
                    "registers": ["0x00BE"],
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    # Offset from 0x003B to 0x00BE = 131
    raw = [0] * 94 + [3]  # Positive → "Discharge"
    result = parse_raw(raw)
    assert result["Battery Status"].startswith("Discharge")


def test_parse_raw_gen_connected_status(monkeypatch):
    fake_defs = [
        {
            "section": "Gen",
            "items": [
                {
                    "titleEN": "Gen-connected Status",
                    "registers": ["0x00A6"],
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    offset = (0x0070 - 0x003B + 1) + (0x00A6 - 0x0096)
    raw = [0] * offset + [0]  # Value 0 = "Off"
    result = parse_raw(raw)
    assert result["Gen-connected Status"] == "Off"
