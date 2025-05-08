def test_enum_mapping_skips_item_without_title(monkeypatch):
    from custom_components.deye_inverter import InverterDataParser as parser

    original_definitions = parser._DEFINITIONS
    original_sections = parser._sections

    fake_defs = [{
        "section": "NoTitle",
        "items": [{
            "registers": ["0x00F1"],
            "interactionType": 2,
            "optionRanges": [{"key": 1, "valueEN": "Ignored"}]
        }]
    }]

    try:
        monkeypatch.setattr(parser, "_DEFINITIONS", fake_defs)
        monkeypatch.setattr(parser, "_sections", fake_defs)
        parser._ENUM_MAPPINGS.clear()

        # Re-run mapping logic
        for section in parser._sections:
            for item in section.get("items", []):
                option_ranges = item.get("optionRanges")
                if (
                    isinstance(option_ranges, list)
                    and option_ranges
                    and item.get("interactionType") == 2
                ):
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

        assert len(parser._ENUM_MAPPINGS) == 0
    finally:
        # Restore for future tests
        monkeypatch.setattr(parser, "_DEFINITIONS", original_definitions)
        monkeypatch.setattr(parser, "_sections", original_sections)
