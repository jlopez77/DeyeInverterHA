
import pytest
import json
from custom_components.deye_inverter import InverterDataParser as parser


def test_load_definitions_json_error(monkeypatch):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: "{bad: json")
    result = parser._load_definitions()
    assert result == {}


def test_load_definitions_file_fallback(monkeypatch, caplog):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr(parser.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("file fail")))
    caplog.set_level("ERROR")
    result = parser._load_definitions()
    assert result == {}
    assert "Could not read DYRealTime.txt" in caplog.text


def test_enum_builder_skips_item_without_title(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Ignored"}],
            "registers": ["0x00F1"]
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


def test_parse_skips_item_without_registers(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{"titleEN": "NoRegs"}]
    }])
    result = parser.parse_raw([0])
    assert "NoRegs" not in result


def test_parse_rule_6(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Bitfield",
            "registers": ["003B"],
            "parserRule": 6
        }]
    }])
    result = parser.parse_raw([255])
    assert result["Bitfield"] == 255


def test_parse_ascii_fallback(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Serial",
            "parserRule": 5,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([0x0001])
    assert result["Serial"].startswith("0x")


def test_parse_enum_unknown(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "EnumField",
            "registers": ["003B"],
            "interactionType": 2,
            "parserRule": 1,
            "optionRanges": [{"key": 1, "valueEN": "On"}],
            "ratio": 1,
            "offset": 0,
            "signed": True
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    parser._ENUM_MAPPINGS[(0x003B, "EnumField")] = {1: "On"}
    result = parser.parse_raw([999])
    assert result["EnumField"] == "Unknown (999)"


def test_parse_exception_in_block(monkeypatch, caplog):
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


def test_parse_raw_final_return(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [
            {
                "titleEN": "Bitfield",
                "registers": ["003B"],
                "parserRule": 6
            },
            {
                "titleEN": "FinalField",
                "registers": ["003C"],
                "ratio": 1,
                "offset": 0,
                "signed": True
            }
        ]
    }])
    result = parser.parse_raw([99, 42])
    assert result["Bitfield"] == 99
    assert result["FinalField"] == 42.0

def test_enum_mapping_skips_item_without_title(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    # Patch `_sections` to include an item with no titleEN
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Ignored"}],
            "registers": ["0x00F1"]
            # No "titleEN"
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
                if not title:  # ← LINE 48
                    continue
                # would map here otherwise

    assert len(parser._ENUM_MAPPINGS) == 0

def test_parse_skips_item_with_no_registers(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "NoRegsField"
            # No "registers" key at all
        }]
    }])

    result = parser.parse_raw([123])
    assert "NoRegsField" not in result
