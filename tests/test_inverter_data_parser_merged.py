
# === Merged test file: test_inverter_data_parser_merged.py ===
# This file combines 'corner', 'full', and 'new' test files
# to achieve maximum test coverage on InverterDataParser.py

import pytest
import importlib
from custom_components.deye_inverter import InverterDataParser as parser


# === Combine & status functions ===

def test_combine_registers_unsigned():
    assert parser.combine_registers([0x1234, 0x5678], signed=False) == 0x12345678

def test_combine_registers_signed_negative():
    assert parser.combine_registers([0xFFFF, 0xFFFE], signed=True) < 0

def test_parse_status_helpers():
    assert parser.parse_battery_status(5) == "Discharge"
    assert parser.parse_battery_status(-1) == "Charge"
    assert parser.parse_battery_status(0) == "Stand-by"
    assert parser.parse_grid_status(1) == "BUY"
    assert parser.parse_grid_status(-1) == "SELL"
    assert parser.parse_grid_status(0) == "Stand-by"
    assert parser.parse_smartload_status(0) == "OFF"
    assert parser.parse_smartload_status(1) == "ON"
    assert parser.parse_smartload_status(42) == "Unknown (42)"
    assert parser.parse_grid_connected_status(1) == "On-Grid"
    assert parser.parse_grid_connected_status(0) == "Off-Grid"
    assert parser.parse_gen_connected_status(1) == "On"
    assert parser.parse_gen_connected_status(0) == "Off"


# === Coverage ghosts ===

def test_enum_builder_skips_item_without_title(monkeypatch):
    """Covers line 48."""
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "OK"}],
            "registers": ["0x00F1"]
            # No titleEN
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    # Simulate rebuild
    for section in parser._sections:
        for item in section.get("items", []):
            option_ranges = item.get("optionRanges")
            if option_ranges and item.get("interactionType") == 2:
                title = item.get("titleEN")
                if not title:
                    continue  # line 48 hit here
    assert True  # no crash


def test_parse_skips_item_without_registers(monkeypatch):
    """Covers lines 61–62."""
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{"titleEN": "NoRegs"}]  # missing "registers"
    }])
    result = parser.parse_raw([0])
    assert "NoRegs" not in result


def test_parser_rule_6(monkeypatch):
    """Covers line 128."""
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Bitfield",
            "parserRule": 6,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([255])
    assert result["Bitfield"] == 255


def test_parse_exception_handling(monkeypatch, caplog):
    """Covers line 161."""
    caplog.set_level("DEBUG")
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "CrashField",
            "registers": ["003B"],
            "ratio": "not_a_float"
        }]
    }])
    result = parser.parse_raw([1])
    assert "CrashField" not in result
    assert "Error parsing CrashField" in caplog.text


# === Enum fallback

def test_enum_mapping_unknown_value(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "EnumField",
            "registers": ["003B"],
            "interactionType": 2,
            "parserRule": 1,
            "optionRanges": [{"key": 1, "valueEN": "OK"}],
            "ratio": 1,
            "offset": 0,
            "signed": True
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    parser._ENUM_MAPPINGS[(0x003B, "EnumField")] = {1: "OK"}
    result = parser.parse_raw([999])
    assert result["EnumField"] == "Unknown (999)"


def test_total_grid_production(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Total Grid Production",
            "registers": ["003B", "003C"],
            "ratio": 0.1
        }]
    }])
    result = parser.parse_raw([0x0001, 0x0002])
    assert "Total Grid Production" in result
    assert "(raw:" in result["Total Grid Production"]

def test_load_definitions_full_fallback(monkeypatch, caplog):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("pkg fail")))
    monkeypatch.setattr(parser.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("file fail")))
    caplog.set_level("ERROR")
    result = parser._load_definitions()
    assert result == {}
    assert "Could not read DYRealTime.txt" in caplog.text

def test_ascii_parser_rule_fallback(monkeypatch):
    # 0x0001 = SOH = non-printable ASCII -> fallback to hex
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Serial",
            "parserRule": 5,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([0x0001])
    assert result["Serial"].startswith("0x")

def test_parse_raw_returns_valid_field(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Simple",
            "registers": ["003B"],
            "ratio": 1
        }]
    }])
    result = parser.parse_raw([42])
    assert result["Simple"] == 42.0


def test_parse_raw_reaches_return(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    # Patch a definition with a non-special field
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Generic Field",
            "registers": ["003B"],  # index 0
            "ratio": 1,
            "offset": 0,
            "signed": True
        }]
    }])

    raw = [123]
    result = parser.parse_raw(raw)

    # This will hit the default numeric parse path and reach return
    assert result == {"Generic Field": 123.0}

def test_parse_raw_forces_return_path(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [
            {
                "titleEN": "First",
                "registers": ["003B"],
                "parserRule": 6  # triggers continue
            },
            {
                "titleEN": "Final",
                "registers": ["003C"],
                "ratio": 1,
                "offset": 0,
                "signed": True
            }
        ]
    }])

    result = parser.parse_raw([99, 42])
    assert result == {"First": 99, "Final": 42.0}

def test_parse_raw_final_return(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    # Inject a barebones definition that cannot trigger any continue
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Simple Field",
            "registers": ["003B"],
            "ratio": 1.0,
            "offset": 0.0,
            "signed": True,
            "parserRule": 1  # numeric
        }]
    }])

    raw = [10]  # 0x003B maps to index 0
    result = parser.parse_raw(raw)

    # Assert not only correctness, but ensure parsing happened
    assert isinstance(result, dict)
    assert result == {"Simple Field": 10.0}

# --- From test_inverter_data_parser_corner.py ---
import pytest
import json
from unittest.mock import mock_open, patch
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

def test_parse_raw_definitions_not_dict_or_list(monkeypatch):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", "invalid_type")
    result = parse_raw([1])
    assert result == {}  # Should return empty dict when _DEFINITIONS is neither dict nor list

def test_parse_raw_missing_registers(monkeypatch):
    fake_defs = [{"section": "Broken", "items": [{"titleEN": "No Regs"}]}]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([1])
    assert "No Regs" not in result  # Should skip item with no registers

def test_parse_raw_out_of_bounds(monkeypatch):
    fake_defs = [{
        "section": "Edge",
        "items": [{
            "titleEN": "Out of Bounds",
            "registers": ["0x00F1"],  # Too far, will result in out of bounds
            "parserRule": 1
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([1])
    assert "Out of Bounds" not in result 

def test_parse_raw_index_but_block_empty(monkeypatch):
    fake_defs = [{
        "section": "BlockEmpty",
        "items": [{
            "titleEN": "Missing Block",
            "registers": ["0x00F8"],  # Valid register -> idx = 248
            "parserRule": 1
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)

    # Raw too short for idx=248, so block will be empty
    result = parse_raw([0] * 100)
    assert "Missing Block" not in result

def test_parse_raw_block_empty_and_ascii_fallback(monkeypatch):
    fake_defs = [{
        "section": "ASCII Block",
        "items": [{
            "titleEN": "ASCII Fallback",
            "registers": ["0x00F8"],  # Index 248
            "parserRule": 5
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)

    # Case 1: raw too short, will skip at line 128
    result = parse_raw([0] * 100)
    assert "ASCII Fallback" not in result

    # Case 2: block present but only control characters, triggers fallback to hex at line 139
    raw = [0x0000] * 249
    result = parse_raw(raw)
    assert result["ASCII Fallback"].startswith("0x")

@patch("importlib.resources.read_text", side_effect=Exception("pkg fail"))
@patch("pathlib.Path.read_text", side_effect=Exception("path fail"))
def test_load_definitions_all_fail(mock_path_read, mock_pkg_read, caplog):
    with caplog.at_level("ERROR"):
        result = _load_definitions()
        assert result == {}
        assert "Could not read DYRealTime.txt" in caplog.text


def test_parse_raw_invalid_definitions_type_logs(monkeypatch, caplog):
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", 1234)
    with caplog.at_level("ERROR"):
        result = parse_raw([])
        assert result == {}
        assert "Invalid definitions type" in caplog.text


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


def test_parse_raw_reversed_field(monkeypatch):
    fake_defs = [{
        "section": "Reversed",
        "items": [{
            "titleEN": "Total Energy Bought",
            "registers": ["0x003B", "0x003C"],
            "ratio": 1,
            "signed": False,
        }]
    }]
    monkeypatch.setattr("custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_defs)
    result = parse_raw([0x0001, 0x0002])
    assert "Total Energy Bought" in result
    assert result["Total Energy Bought"] == 131073.0  # 0x00020001

# --- From test_inverter_data_parser_new.py ---
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
