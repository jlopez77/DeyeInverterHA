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
            if option_ranges and item.get("interactionType") == 2:
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
            if option_ranges and item.get("interactionType") == 2:
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
    assert (0x00F1, "InvalidOptionRanges") not in parser._ENUM_MAPPINGS

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
    assert len(parser._ENUM_MAPPINGS) == 0

def test_empty_definitions(monkeypatch):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: "[]")
    definitions = parser._load_definitions()
    assert isinstance(definitions, list)
    assert definitions == []
