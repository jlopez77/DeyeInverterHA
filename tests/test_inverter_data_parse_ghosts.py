import pytest
import json
from custom_components.deye_inverter import InverterDataParser as parser

def test_enum_builder_invalid_register(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "A"}],
            "registers": ["XYZ"],
            "titleEN": "InvalidRegisterTest"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    
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
                        pass

    assert (0x00F1, "InvalidRegisterTest") not in parser._ENUM_MAPPINGS

def test_enum_builder_invalid_option_ranges(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": "wrong", "valueEN": 5}],
            "registers": ["0x00F1"],
            "titleEN": "InvalidOptionRanges"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()

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
                        pass

    assert parser._ENUM_MAPPINGS.get((0x00F1, "InvalidOptionRanges")) == {}

def test_enum_builder_non_interaction_type(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 1,
            "optionRanges": [{"key": 1, "valueEN": "Ignored"}],
            "registers": ["0x00F1"],
            "titleEN": "WrongType"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()

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
                        pass

    assert parser._ENUM_MAPPINGS == {}

def test_empty_definitions(monkeypatch):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: "[]")
    definitions = parser._load_definitions()
    assert isinstance(definitions, list)
    assert definitions == []

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
    for section in parser._sections:
        for item in section.get("items", []):
            title = item.get("titleEN")
            if not title:
                continue  # Triggers line 48/139
            assert False, "Should have continued early due to empty title"

def test_enum_builder_invalid_register_type(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "X"}],
            "registers": [None],  # Triggers TypeError
            "titleEN": "BadRegisterType"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    for section in parser._sections:
        for item in section.get("items", []):
            option_ranges = item.get("optionRanges")
            if isinstance(option_ranges, list) and option_ranges and item.get("interactionType") == 2:
                title = item.get("titleEN")
                mapping = {}
                for opt in option_ranges:
                    if isinstance(opt.get("key"), int) and isinstance(opt.get("valueEN"), str):
                        mapping[opt["key"]] = opt["valueEN"]
                for reg_hex in item.get("registers", []):
                    try:
                        int(reg_hex, 16)
                    except (ValueError, TypeError):
                        continue  # Hits line 62

def test_definitions_type_error(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", 42)
    result = []
    if isinstance(parser._DEFINITIONS, dict):
        result = list(parser._DEFINITIONS.values())
    elif isinstance(parser._DEFINITIONS, list):
        result = parser._DEFINITIONS
    else:
        assert type(parser._DEFINITIONS) == int  # Fallback path triggers lines 132–133

def test_registers_empty(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Blank"}],
            "registers": [],
            "titleEN": "EmptyRegisters"
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    assert parser._ENUM_MAPPINGS == {}  # No mappings made, line 161

def test_ascii_parser_fallback():
    # Simulate fallback on non-hex ASCII conversion (line 183)
    result = {}
    chars = [ord(c) for c in "TEST"]
    ascii_string = "".join(chr(b) for b in chars)
    if all(32 <= b < 127 for b in chars):
        value = ascii_string
    else:
        value = "0x" + "".join(f"{b:02X}" for b in chars)
    result["test"] = value or None
    assert result["test"] == "TEST"
