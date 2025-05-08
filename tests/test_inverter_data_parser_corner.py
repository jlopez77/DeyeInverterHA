import pytest
import json
from unittest.mock import patch
from custom_components.deye_inverter.InverterDataParser import (
    _load_definitions,
    parse_raw,
    combine_registers,
    _ENUM_MAPPINGS,
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


def test_load_definitions_all_fail(monkeypatch, caplog):
    monkeypatch.setattr("importlib.resources.read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr("pathlib.Path.read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("no file")))
    with caplog.at_level("ERROR"):
        result = _load_definitions()
        assert result == {}
        assert "Could not read DYRealTime.txt" in caplog.text


def test_combine_registers_reverse():
    value = combine_registers([0x0001, 0x0002], signed=False, reverse=True)
    assert value == 0x00020001


def test_parse_raw_ascii_valid(monkeypatch):
    fake_defs = [{
        "section": "ASCII",
        "items": [{"titleEN": "Valid ASCII", "registers": ["0x003B"], "parserRule": 5}]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    raw = [0x4869]  # "Hi"
    result = parse_raw(raw)
    assert result["Valid ASCII"] == "Hi"


def test_parse_raw_ascii_control_char(monkeypatch):
    fake_defs = [{
        "section": "ASCII",
        "items": [{"titleEN": "Serial", "registers": ["0x003B"], "parserRule": 5}]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    raw = [0x0001]  # control char
    result = parse_raw(raw)
    assert result["Serial"].startswith("0x")


def test_parse_raw_empty_block(monkeypatch):
    fake_defs = [{
        "section": "EmptyBlock",
        "items": [{"titleEN": "Missing", "registers": ["0x00F8"]}]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([0] * 100)
    assert "Missing" not in result


def test_parse_raw_default_numeric(monkeypatch):
    fake_defs = [{
        "section": "Numeric",
        "items": [{"titleEN": "Power", "registers": ["0x003B"], "ratio": 2, "offset": 1}]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([10])
    assert result["Power"] == 21.0


def test_parse_raw_offset_cast_fails(monkeypatch, caplog):
    fake_defs = [{
        "section": "Error",
        "items": [{"titleEN": "Bad Offset", "registers": ["0x003B"], "offset": "not_a_float"}]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    with caplog.at_level("DEBUG"):
        result = parse_raw([1])
        assert "Bad Offset" not in result
        assert "Error parsing Bad Offset" in caplog.text


def test_parse_raw_invalid_definitions_type(monkeypatch, caplog):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", 1234)
    with caplog.at_level("ERROR"):
        result = parse_raw([])
        assert result == {}
        assert "Invalid definitions type" in caplog.text


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
            ]
        }]
    }]

    monkeypatch.setattr(parser, "_DEFINITIONS", fake_defs)
    parser._ENUM_MAPPINGS.clear()
    parser._ENUM_MAPPINGS[(0x0097, "Enum Test")] = {1: "Enabled", 2: "Disabled"}

    offset = (0x0070 - 0x003B + 1) + (0x0097 - 0x0096)
    raw = [0] * offset + [999]
    result = parser.parse_raw(raw)
    assert result["Enum Test"] == "Unknown (999)"
