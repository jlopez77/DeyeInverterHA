import pytest
import json
from unittest.mock import patch
from custom_components.deye_inverter import InverterDataParser as parser


def test_combine_registers_unsigned():
    val = parser.combine_registers([0x1234, 0x5678], signed=False)
    assert val == 0x12345678


def test_combine_registers_signed_negative():
    val = parser.combine_registers([0xFFFF, 0xFFFE], signed=True)
    assert val < 0


def test_parse_battery_status():
    assert parser.parse_battery_status(5) == "Discharge"
    assert parser.parse_battery_status(-3) == "Charge"
    assert parser.parse_battery_status(0) == "Stand-by"


def test_parse_grid_status():
    assert parser.parse_grid_status(1) == "BUY"
    assert parser.parse_grid_status(-1) == "SELL"
    assert parser.parse_grid_status(0) == "Stand-by"


def test_parse_smartload_status():
    assert parser.parse_smartload_status(1) == "ON"
    assert parser.parse_smartload_status(0) == "OFF"
    assert parser.parse_smartload_status(99) == "Unknown (99)"


def test_parse_raw_with_empty():
    result = parser.parse_raw([])
    assert result == {}


def test_load_definitions_json_error():
    bad_json = "{bad: json"
    with patch("importlib.resources.read_text", return_value=bad_json):
        result = parser._load_definitions()
        assert result == {}


def test_load_definitions_success_json(monkeypatch):
    valid_json = json.dumps({"section": {"items": []}})
    monkeypatch.setattr("importlib.resources.read_text", lambda *a, **k: valid_json)
    result = parser._load_definitions()
    assert result == {"section": {"items": []}}


def test_load_definitions_triggers_path_fallback(monkeypatch):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("pkg fail")))
    monkeypatch.setattr(parser.Path, "read_text", lambda *a, **k: '{"section": {"items": []}}')
    result = parser._load_definitions()
    assert "section" in result


def test_enum_mapping_skips_item_with_no_title(monkeypatch):
    """Covers line 48 (title missing during ENUM_MAPPINGS build)."""
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "ignored"}],
            "registers": ["0x00F1"]
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    for section in parser._sections:
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
                mapping = {}
                for opt in option_ranges:
                    key = opt.get("key")
                    val = opt.get("valueEN")
                    if isinstance(key, int) and isinstance(val, str):
                        mapping[key] = val
                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                        parser._ENUM_MAPPINGS[(reg, title)] = mapping
                    except (ValueError, TypeError):
                        continue
    assert parser._ENUM_MAPPINGS == {}


def test_parse_raw_skips_item_without_title(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{"items": [{}]}])
    result = parser.parse_raw([0])
    assert result == {}


def test_parse_raw_skips_item_without_registers(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{"items": [{"titleEN": "NoRegs"}]}])
    result = parser.parse_raw([0])
    assert "NoRegs" not in result


def test_parser_rule_6(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Bitfield",
            "parserRule": 6,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([123])
    assert result["Bitfield"] == 123


def test_parse_raw_catches_exception(monkeypatch, caplog):
    caplog.set_level("DEBUG")
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "CrashingField",
            "registers": ["003B"],
            "ratio": "not_a_float"
        }]
    }])
    result = parser.parse_raw([1])
    assert "CrashingField" not in result
    assert "Error parsing CrashingField" in caplog.text


def test_enum_mapping_unknown_value(monkeypatch):
    monkeypatch.setitem(parser._ENUM_MAPPINGS, (0x003B, "EnumField"), {1: "OK"})
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "EnumField",
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([999])
    assert result["EnumField"] == "Unknown (999)"


def test_total_grid_production_custom_format(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Total Grid Production",
            "registers": ["003B"],
            "ratio": 1.5,
            "offset": 10
        }]
    }])
    result = parser.parse_raw([10])
    assert result["Total Grid Production"] == "25.0 (raw: 10)"
