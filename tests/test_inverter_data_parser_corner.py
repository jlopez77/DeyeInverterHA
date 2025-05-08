import pytest
import json
from unittest.mock import mock_open, patch
from custom_components.deye_inverter.InverterDataParser import (
    _load_definitions,
    parse_raw,
    combine_registers,
    _ENUM_MAPPINGS,
    _DEFINITIONS,
)


def test_load_definitions_json_error():
    bad_json = "{bad: json"  # Invalid JSON
    with patch("importlib.resources.read_text", return_value=bad_json):
        result = _load_definitions()
        assert result == {}  # Should fallback to empty dict


def test_load_definitions_fallback_file():
    fallback_json = json.dumps({"section": {"items": []}})
    with patch("importlib.resources.read_text", side_effect=Exception()), \
         patch("pathlib.Path.read_text", return_value=fallback_json):
        result = _load_definitions()
        assert "section" in result


def test_combine_registers_reverse():
    value = combine_registers([0x0001, 0x0002], signed=False, reverse=True)
    assert value == 0x00020001


def test_parse_raw_ascii_control_char(monkeypatch):
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
    result = parse_raw([0x0001])
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
    raw = [0] * 94 + [3]
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
    raw = [0] * offset + [0]
    result = parse_raw(raw)
    assert result["Gen-connected Status"] == "Off"


def test_parse_raw_enum_mapping(monkeypatch):
    """Test parsing with enum mapping fallback."""
    fake_defs = [
        {
            "section": "Test",
            "items": [
                {
                    "titleEN": "Mode Status",
                    "registers": ["0x00F1"],
                    "interactionType": 2,
                    "parserRule": 1,
                    "optionRanges": [
                        {"key": 1, "valueEN": "Auto"},
                        {"key": 2, "valueEN": "Manual"},
                    ],
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)

    # Rebuild _ENUM_MAPPINGS
    _ENUM_MAPPINGS.clear()
    for section in fake_defs:
        for item in section.get("items", []):
            option_ranges = item.get("optionRanges")
            if (
                isinstance(option_ranges, list)
                and option_ranges
                and item.get("interactionType") == 2
            ):
                title = item.get("titleEN")
                if not title:
                    continue
                mapping = {
                    opt["key"]: opt["valueEN"]
                    for opt in option_ranges
                    if "key" in opt and "valueEN" in opt
                }
                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                        _ENUM_MAPPINGS[(reg, title)] = mapping
                    except (ValueError, TypeError):
                        continue

    raw = [0] * (0x00F1 - 0x003B) + [2]
    result = parse_raw(raw)
    assert result["Mode Status"].startswith("Manual")


def test_parse_raw_enum_unknown(monkeypatch):
    """Test fallback when enum value is unknown."""
    fake_defs = [
        {
            "section": "Test",
            "items": [
                {
                    "titleEN": "Mode Status",
                    "registers": ["0x00F1"],
                    "interactionType": 2,
                    "parserRule": 1,
                    "optionRanges": [
                        {"key": 1, "valueEN": "Auto"},
                    ],
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)

    # Rebuild _ENUM_MAPPINGS
    _ENUM_MAPPINGS.clear()
    for section in fake_defs:
        for item in section.get("items", []):
            option_ranges = item.get("optionRanges")
            if (
                isinstance(option_ranges, list)
                and option_ranges
                and item.get("interactionType") == 2
            ):
                title = item.get("titleEN")
                if not title:
                    continue
                mapping = {
                    opt["key"]: opt["valueEN"]
                    for opt in option_ranges
                    if "key" in opt and "valueEN" in opt
                }
                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                        _ENUM_MAPPINGS[(reg, title)] = mapping
                    except (ValueError, TypeError):
                        continue

    raw = [0] * (0x00F1 - 0x003B) + [999]
    result = parse_raw(raw)
    assert result["Mode Status"] == "Unknown (999)"
