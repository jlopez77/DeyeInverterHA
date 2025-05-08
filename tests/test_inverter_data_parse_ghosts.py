import json
import importlib
import logging
from pathlib import Path

import pytest

from custom_components.deye_inverter import InverterDataParser as parser


def reload_parser():
    # Force re-import so that _DEFINITIONS and _sections are rebuilt
    importlib.reload(parser)


def test_load_definitions_file_not_found(monkeypatch, caplog):
    """Cover the fp.read_text exception path (lines ~48)."""
    # make pkg_resources.read_text throw, and Path.read_text also throw
    monkeypatch.setattr(parser.pkg_resources, "read_text",
                        lambda pkg, name: (_ for _ in ()).throw(Exception("oops")))
    monkeypatch.setattr(Path, "read_text",
                        lambda self: (_ for _ in ()).throw(IOError("no file")))
    caplog.set_level(logging.ERROR)
    reload_parser()
    # _DEFINITIONS should fall back to {}
    assert parser._DEFINITIONS == {}
    assert "Could not read DYRealTime.txt" in caplog.text


def test_load_definitions_json_decode_error(monkeypatch, caplog):
    """Cover the JSONDecodeError branch (lines ~61–62)."""
    # have read_text return invalid JSON
    monkeypatch.setattr(parser.pkg_resources, "read_text", lambda pkg, name: "not valid json")
    caplog.set_level(logging.ERROR)
    reload_parser()
    assert parser._DEFINITIONS == {}
    assert "Error parsing DYRealTime.txt" in caplog.text


@pytest.fixture(autouse=True)
def fresh_sections():
    """Reset parser._sections and mappings for each test."""
    parser._sections = []
    parser._ENUM_MAPPINGS.clear()
    return parser


def make_section(item):
    return {"RealTimeResponse": [item]}


def test_enum_branch(fresh_sections):
    """Cover the enum-mapping branch."""
    item = {
        "Name": "Foo.Status",
        "Index": 0,
        "Title": "Status",
        "EnumType": [{"Value": 1, "Text": "OK"}]
    }
    fresh_sections._sections = [make_section(item)]
    # manually insert mapping
    fresh_sections._ENUM_MAPPINGS[(0, "Status")] = {1: "OK"}
    result = fresh_sections.parse_raw([1])
    assert result["Status"] == "OK"


def test_hex_branch(fresh_sections):
    """Cover display_format == 'Hex' (line ~128)."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.Code",
            "Index": 0,
            "Title": "Code",
            "DisplayFormat": "Hex"
        })
    ]
    out = fresh_sections.parse_raw([255])
    assert out["Code"] == hex(255)


def test_raw_branch(fresh_sections):
    """Cover display_format == 'Raw' (line ~132)."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.RawVal",
            "Index": 0,
            "Title": "RawVal",
            "DisplayFormat": "Raw"
        })
    ]
    out = fresh_sections.parse_raw([42])
    assert out["RawVal"] == 42


def test_custom_display_format(fresh_sections):
    """Cover arbitrary DisplayFormat template (line ~139)."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.TempStr",
            "Index": 0,
            "Title": "TempStr",
            "DisplayFormat": "Value={value}!"
        })
    ]
    out = fresh_sections.parse_raw([99])
    assert out["TempStr"] == "Value=99!"


def test_time_branch(fresh_sections):
    """Cover Time formatting branch (line ~161)."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.RunTime",
            "Index": 0,
            "Title": "RunTime"
        })
    ]
    out = fresh_sections.parse_raw([930])
    assert out["RunTime"] == "09:30"


def test_percent_unit_branch(fresh_sections):
    """Cover percentage formatting (unit '%' branch)."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.Load",
            "Index": 0,
            "Title": "Load",
            "Unit": "%"
        })
    ]
    out = fresh_sections.parse_raw([50])
    assert out["Load"].startswith("50.0%")
    assert "(raw: 50)" in out["Load"]


def test_default_numeric_branch(fresh_sections):
    """Cover the final default numeric branch."""
    fresh_sections._sections = [
        make_section({
            "Name": "Foo.Value",
            "Index": 0,
            "Title": "Value"
        })
    ]
    out = fresh_sections.parse_raw([123])
    assert isinstance(out["Value"], float)
    assert out["Value"] == 123.0


# Backwards compatibility alias
parse_realtime = parse_raw
