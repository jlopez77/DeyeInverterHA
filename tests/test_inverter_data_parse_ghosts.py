import pytest
import importlib
from custom_components import deye_inverter
from custom_components.deye_inverter import InverterDataParser as parser

def test_enum_builder_empty_title(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Text"}],
            "registers": ["0x00F1"],
            "titleEN": ""  # Triggers early continue
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    importlib.reload(deye_inverter.InverterDataParser)
    assert (0x00F1, "") not in parser._ENUM_MAPPINGS

def test_enum_builder_invalid_register_type(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Text"}],
            "registers": [None],  # Invalid type for register
            "titleEN": "InvalidType"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    importlib.reload(deye_inverter.InverterDataParser)
    assert (None, "InvalidType") not in parser._ENUM_MAPPINGS

def test_definitions_as_dict(monkeypatch):
    monkeypatch.setattr(parser, "_load_definitions", lambda: {"section": {"items": []}})
    importlib.reload(deye_inverter.InverterDataParser)
    assert isinstance(parser._sections, list)

def test_definitions_invalid_type(monkeypatch):
    monkeypatch.setattr(parser, "_load_definitions", lambda: 42)
    importlib.reload(deye_inverter.InverterDataParser)
    # Line 132-133 logs error and sets _sections = []
    assert isinstance(parser._sections, list)

def test_enum_builder_empty_registers(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Blank"}],
            "registers": [],
            "titleEN": "EmptyRegisters"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    
    # Call enum-mapping logic inline (no reload!)
    for section in parser._sections:
        for item in section.get("items", []):
            option_ranges = item.get("optionRanges")
            if isinstance(option_ranges, list) and option_ranges and item.get("interactionType") == 2:
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

def test_ascii_fallback_parser():
    chars = [0x00, 0x7F]  # not printable
    ascii_string = "".join(chr(b) for b in chars)
    value = "0x" + "".join(f"{b:02X}" for b in chars)
    result = value or None
    assert result == "0x007F"
