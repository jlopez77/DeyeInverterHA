import pytest
import json
from unittest.mock import patch
from custom_components.deye_inverter.InverterDataParser import (
    _load_definitions,
    parse_raw,
    combine_registers,
    _ENUM_MAPPINGS,
    _DEFINITIONS
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

def test_parse_raw_invalid_definitions(monkeypatch):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", 42)
    result = parse_raw([])
    assert result == {}

def test_parse_raw_offset_cast_fails(monkeypatch, caplog):
    fake_defs = [{
        "section": "X",
        "items": [{
            "titleEN": "Bad Offset",
            "registers": ["0x003B"],
            "offset": "not_a_float"
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    with caplog.at_level("DEBUG"):
        result = parse_raw([1])
        assert "Bad Offset" not in result
        assert "Error parsing Bad Offset" in caplog.text

def test_parse_raw_ascii_decode_fallback(monkeypatch):
    fake_defs = [{
        "section": "ControlASCII",
        "items": [{
            "titleEN": "Serial",
            "registers": ["0x003B"],
            "parserRule": 5
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([0x0001])  # control char => fallback
    assert result["Serial"].startswith("0x")

def test_parse_raw_missing_block(monkeypatch):
    fake_defs = [{
        "section": "Skip",
        "items": [{
            "titleEN": "Empty",
            "registers": ["0x00F8"],
            "parserRule": 5
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([0] * 100)  # not enough length
    assert "Empty" not in result

def test_parse_raw_enum_unknown(monkeypatch):
    fake_defs = [{
        "section": "Enum",
        "items": [{
            "titleEN": "Status",
            "registers": ["0x0096"],
            "interactionType": 2,
            "parserRule": 1,
            "optionRanges": [{"key": 1, "valueEN": "On"}]
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    _ENUM_MAPPINGS.clear()
    _ENUM_MAPPINGS[(0x0096, "Status")] = {1: "On"}
    offset = (0x0070 - 0x003B + 1)
    result = parse_raw([0] * offset + [999])
    assert result["Status"] == "Unknown (999)"

def test_parse_raw_temperature_adjustment(monkeypatch):
    fake_defs = [{
        "section": "Temp",
        "items": [{
            "titleEN": "Ambient Temperature",
            "registers": ["0x003B"],
            "ratio": 1,
            "signed": True
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([150])
    assert result["Ambient Temperature"] == 50.0

def test_parse_enum_fallback(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    fake_defs = [{
        "section": "Fake",
        "items": [{
            "titleEN": "Enum Test",
            "registers": ["0x0097"],
            "interactionType": 2,
            "parserRule": 1,
            "optionRanges": [
                {"key": 1, "valueEN": "Enabled"},
                {"key": 2, "valueEN": "Disabled"},
            ],
        }]
    }]

    monkeypatch.setattr(parser, "_DEFINITIONS", fake_defs)
    parser._ENUM_MAPPINGS.clear()
    parser._ENUM_MAPPINGS[(0x0097, "Enum Test")] = {1: "Enabled", 2: "Disabled"}

    offset = (0x0070 - 0x003B + 1) + (0x0097 - 0x0096)
    raw = [0] * offset + [999]

    result = parser.parse_raw(raw)
    assert result["Enum Test"] == "Unknown (999)"

def test_load_definitions_triggers_path_fallback(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("pkg fail")))
    monkeypatch.setattr(parser.Path, "read_text", lambda *a, **k: '{"section": {"items": []}}')

    result = parser._load_definitions()
    assert "section" in result

def test_enum_mapping_skips_item_without_title(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser
    import importlib

    fake_defs = [{
        "section": "NoTitle",
        "items": [{
            "registers": ["0x00F1"],
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Ignored"}]
            # titleEN missing on purpose
        }]
    }]

    monkeypatch.setattr(parser, "_DEFINITIONS", fake_defs)

    # Clear and reload to re-trigger prebuild loop
    parser._ENUM_MAPPINGS.clear()
    importlib.reload(parser)

    # Check that no enum mapping was created
    assert not any("Ignored" in v for m in parser._ENUM_MAPPINGS.values() for v in m.values())
