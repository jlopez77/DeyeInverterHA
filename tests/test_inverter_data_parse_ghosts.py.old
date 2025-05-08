import pytest
import importlib
from custom_components.deye_inverter import InverterDataParser as parser

def test_enum_builder_skips_item_without_title(monkeypatch):
    monkeypatch.setattr(parser, "_sections", [{
        "items": [{
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "On"}],
            "registers": ["0x00FF"]
            # Missing titleEN
        }]
    }])
    parser._ENUM_MAPPINGS.clear()
    importlib.reload(parser)
    assert (0x00FF, None) not in parser._ENUM_MAPPINGS


def test_parse_raw_skips_item_without_registers(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{"items": [{"titleEN": "NoRegs"}]}])
    result = parser.parse_raw([0])
    assert "NoRegs" not in result


def test_parser_rule_6_hits(monkeypatch):
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Bitfield",
            "parserRule": 6,
            "registers": ["003B"]
        }]
    }])
    result = parser.parse_raw([123])
    assert result["Bitfield"] == 123


def test_parse_raw_raises_and_catches(monkeypatch, caplog):
    caplog.set_level("DEBUG")
    monkeypatch.setattr(parser, "_DEFINITIONS", [{
        "items": [{
            "titleEN": "Boom",
            "registers": ["003B"],
            "ratio": "not_a_float"
        }]
    }])
    result = parser.parse_raw([1])
    assert "Boom" not in result
    assert "Error parsing Boom" in caplog.text
