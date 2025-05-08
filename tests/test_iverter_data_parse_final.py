import pytest
from custom_components.deye_inverter import InverterDataParser as parser


def test_load_definitions_fallback_both_fail(monkeypatch, caplog):
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr(parser.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(Exception("file fail")))

    caplog.set_level("ERROR")
    definitions = parser._load_definitions()
    assert definitions == {}
    assert "Could not read DYRealTime.txt: file fail" in caplog.text


def test_parse_raw_skips_item_without_title(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{"items": [{}]}])
    result = parser.parse_raw([0] * 200)
    assert result == {}


def test_parse_raw_skips_item_without_registers(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{"items": [{"titleEN": "NoRegs"}]}])
    result = parser.parse_raw([0] * 200)
    assert "NoRegs" not in result


def test_parser_rule_6_alert(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "AlertField",
            "parserRule": 6,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([42])
    assert result["AlertField"] == 42


def test_enum_mapping_unknown_value(monkeypatch):
    monkeypatch.setitem(parser._ENUM_MAPPINGS, (0x00AA, "EnumField"), {1: "Valid"})
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "EnumField",
            "registers": ["00AA"]
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


def test_parse_raw_catches_exception(monkeypatch, caplog):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "CrashingField",
            "registers": ["003B"],
            "ratio": "not_a_float"
        }]
    }])
    caplog.set_level("DEBUG")
    result = parser.parse_raw([1])
    assert "CrashingField" not in result
    assert "Error parsing CrashingField" in caplog.text
