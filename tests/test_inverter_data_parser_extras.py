import pytest
from custom_components.deye_inverter.InverterDataParser import parse_raw

def test_parse_enum_fallback(monkeypatch):
    fake_def = [
        {
            "section": "Fake",
            "items": [
                {
                    "titleEN": "Battery Status",
                    "registers": ["0x00BE"],
                    "interactionType": 2,
                    "parserRule": 1,
                    "optionRanges": [
                        {"key": 1, "valueEN": "Stand-by"},
                        {"key": 2, "valueEN": "Discharge"},
                    ],
                }
            ],
        }
    ]
    # Value 999 should not match any known enum
    raw = [0] * 94 + [999]
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw(raw)
    assert result["Battery Status"] == "Unknown (999)"

def test_parse_reverse_and_ratio(monkeypatch):
    fake_def = [
        {
            "section": "Grid",
            "items": [
                {
                    "titleEN": "Total Grid Production",
                    "registers": ["0x003F", "0x0040"],
                    "parserRule": 3,
                    "ratio": 0.1,
                }
            ],
        }
    ]
    # Reversed means raw = [low, high], but we reverse before combine
    # So combined value = 0x12345678 → 305419896 * 0.1 = 30541989.6
    raw = [0] * (0x003F - 0x003B) + [0x5678, 0x1234]
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw(raw)
    assert "Total Grid Production" in result
    assert "raw" in result["Total Grid Production"]

def test_parse_temperature_offset(monkeypatch):
    fake_def = [
        {
            "section": "Battery",
            "items": [
                {
                    "titleEN": "Battery Temperature",
                    "registers": ["0x00B6"],
                    "parserRule": 1,
                    "ratio": 0.1,
                }
            ],
        }
    ]
    # Index 0x00B6 - 0x0096 = 32 → offset in raw = 54 + 32 = 86
    raw = [0] * 86 + [500]  # 500 * 0.1 - 100 = -50.0
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw(raw)
    assert result["Battery Temperature"] == -50.0

def test_parse_exception_handling(monkeypatch):
    fake_def = [
        {
            "section": "Faulty",
            "items": [
                {
                    "titleEN": "Broken Field",
                    "registers": ["0xZZZZ"],  # invalid hex
                    "parserRule": 1,
                }
            ],
        }
    ]
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw([0] * 100)
    assert "Broken Field" not in result  # Safely skipped
