import pytest
import json
from unittest.mock import mock_open, patch
from custom_components.deye_inverter.InverterDataParser import (
    _load_definitions,
    parse_raw,
    combine_registers,
    _ENUM_MAPPINGS
)

def test_load_definitions_json_error():
    bad_json = "{bad: json"
    with patch("importlib.resources.read_text", return_value=bad_json):
        result = _load_definitions()
        assert result == {}

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
    _ENUM_MAPPINGS.clear()
    for item in fake_defs[0]["items"]:
        reg = int(item["registers"][0], 16)
        title = item["titleEN"]
        mapping = {opt["key"]: opt["valueEN"] for opt in item["optionRanges"]}
        _ENUM_MAPPINGS[(reg, title)] = mapping
    raw = [0] * 242
    raw[241] = 2
    result = parse_raw(raw)
    assert result["Mode Status"] == "Manual (2)"

def test_parse_raw_enum_unknown(monkeypatch):
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
    _ENUM_MAPPINGS.clear()
    for item in fake_defs[0]["items"]:
        reg = int(item["registers"][0], 16)
        title = item["titleEN"]
        mapping = {opt["key"]: opt["valueEN"] for opt in item["optionRanges"]}
        _ENUM_MAPPINGS[(reg, title)] = mapping
    raw = [0] * 242
    raw[241] = 999
    result = parse_raw(raw)
    assert result["Mode Status"] == "Unknown (999)"

def test_parse_raw_invalid_definitions(monkeypatch):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", 42)
    result = parse_raw([])
    assert result == {}

def test_parse_raw_ascii_invalid_bytes(monkeypatch):
    fake_defs = [
        {
            "section": "ASCII",
            "items": [
                {
                    "titleEN": "Model",
                    "registers": ["0x003B", "0x003C"],
                    "parserRule": 5,
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    raw = [0x0000, 0x0001]  # non-printable bytes
    result = parse_raw(raw)
    assert result["Model"].startswith("0x")

def test_parse_raw_custom_parser_raises(monkeypatch):
    fake_defs = [
        {
            "section": "Faulty",
            "items": [
                {
                    "titleEN": "Bad Field",
                    "registers": ["0x003B"],
                }
            ],
        }
    ]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser.combine_registers", lambda *_: (_ for _ in ()).throw(Exception("fail")))
    result = parse_raw([0x0001])
    assert "Bad Field" not in result

def test_load_definitions_fallback_file_missing(monkeypatch, caplog):
    monkeypatch.setattr("importlib.resources.read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("pathlib.Path.read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("no file")))
    from custom_components.deye_inverter.InverterDataParser import _load_definitions
    with caplog.at_level("ERROR"):
        result = _load_definitions()
        assert result == {}
        assert "Could not read DYRealTime.txt" in caplog.text


def test_parse_raw_invalid_definitions_type(monkeypatch, caplog):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", 1234)
    from custom_components.deye_inverter.InverterDataParser import parse_raw
    with caplog.at_level("ERROR"):
        result = parse_raw([0])
        assert result == {}
        assert "Invalid definitions type" in caplog.text


def test_parse_raw_empty_registers(monkeypatch):
    fake_defs = [{"section": "X", "items": [{"titleEN": "Empty Regs", "registers": []}]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([1, 2, 3])
    assert "Empty Regs" not in result


def test_parse_raw_empty_block(monkeypatch):
    fake_defs = [{"section": "X", "items": [{"titleEN": "Bad Index", "registers": ["0xFFFF"]}]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([0] * 10)
    assert "Bad Index" not in result


def test_parse_raw_parser_rule_6(monkeypatch):
    fake_defs = [{"section": "Alerts", "items": [{
        "titleEN": "Alert Flags",
        "registers": ["0x003B"],
        "parserRule": 6,
    }]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([123])
    assert result["Alert Flags"] == 123


def test_parse_raw_temperature_adjustment(monkeypatch):
    fake_defs = [{"section": "Temp", "items": [{
        "titleEN": "Ambient Temperature",
        "registers": ["0x003B"],
        "ratio": 1,
        "signed": True,
    }]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([150])
    assert result["Ambient Temperature"] == 50.0  # 150 * 1 - 100


def test_parse_raw_exception(monkeypatch, caplog):
    fake_defs = [{"section": "Oops", "items": [{
        "titleEN": "Error Field",
        "registers": ["0x003B"],
        "ratio": "not_a_float",  # Will cause ValueError
    }]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    
    with caplog.at_level("DEBUG"):
        try:
            parse_raw([1])
        except Exception:
            pass  # We only care that the exception was logged
        assert "Error parsing Error Field" in caplog.text
