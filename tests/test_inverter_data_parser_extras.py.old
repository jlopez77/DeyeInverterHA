import pytest
from custom_components.deye_inverter.InverterDataParser import parse_raw, _ENUM_MAPPINGS

def test_parse_enum_fallback(monkeypatch):
    """Test that unknown enum values return 'Unknown (...)'."""
    fake_def = [
        {
            "section": "Fake",
            "items": [
                {
                    "titleEN": "Enum Test",
                    "registers": ["0x0097"],
                    "interactionType": 2,
                    "parserRule": 1,
                    "optionRanges": [
                        {"key": 1, "valueEN": "Enabled"},
                        {"key": 2, "valueEN": "Disabled"},
                    ],
                }
            ],
        }
    ]

    # Patch the definitions
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )

    # Patch the _ENUM_MAPPINGS manually
    _ENUM_MAPPINGS.clear()
    _ENUM_MAPPINGS[(0x0097, "Enum Test")] = {1: "Enabled", 2: "Disabled"}

    # Calculate correct offset for register 0x0097
    offset = (0x0070 - 0x003B + 1) + (0x0097 - 0x0096)
    raw = [0] * offset + [999]

    result = parse_raw(raw)
    assert result["Enum Test"] == "Unknown (999)"

def test_parse_reverse_and_ratio(monkeypatch):
    """Test that reversed fields are parsed correctly."""
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
    raw = [0] * (0x003F - 0x003B) + [0x5678, 0x1234]  # reversed = 0x12345678
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw(raw)
    assert "Total Grid Production" in result
    assert "raw" in result["Total Grid Production"]
    assert result["Total Grid Production"].startswith("30541989")

def test_parse_temperature_offset(monkeypatch):
    """Test temperature field is offset by -100."""
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
    # 0x00B6 is in second block, so index = 54 + (0x00B6 - 0x0096) = 86
    raw = [0] * 86 + [500]  # 500 * 0.1 - 100 = -50.0
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw(raw)
    assert result["Battery Temperature"] == -50.0

def test_parse_exception_handling(monkeypatch):
    """Test that invalid register format is gracefully skipped."""
    fake_def = [
        {
            "section": "Faulty",
            "items": [
                {
                    "titleEN": "Broken Field",
                    "registers": ["0xZZZZ"],  # Invalid hex
                    "parserRule": 1,
                }
            ],
        }
    ]
    monkeypatch.setattr(
        "custom_components.deye_inverter.InverterDataParser._DEFINITIONS", fake_def
    )
    result = parse_raw([0] * 100)
    assert "Broken Field" not in result
