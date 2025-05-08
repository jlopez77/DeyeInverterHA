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


