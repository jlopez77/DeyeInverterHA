"""Tests for the per-model scaling variants ("mod")."""

import pytest

from custom_components.deye_inverter.const import (
    DEFAULT_MOD,
    MOD_VARIANTS,
    REGISTER_BLOCKS,
)
from custom_components.deye_inverter.entity_descriptions import build_descriptions
from custom_components.deye_inverter.InverterDataParser import (
    _RAW_DEFINITIONS,
    iter_sections,
    parse_raw,
    register_index,
    resolve_variant,
    select_variant,
)
from custom_components.deye_inverter.profiles import (
    Profile,
    get_profile,
    normalize_mod,
)

RAW_LEN = sum(end - start + 1 for start, end in REGISTER_BLOCKS)


def _raw_sample():
    """Raw registers with the values measured on a real 10 kW inverter."""
    raw = [0] * RAW_LEN
    raw[register_index(0x00B2)] = 301  # Total Load Power
    raw[register_index(0x00B0)] = 301  # Load L1 Power
    raw[register_index(0x00A9)] = 0x10000 - 432  # Total Grid Power, exporting
    raw[register_index(0x00AA)] = 0x10000 - 432  # External CT L1 Power
    raw[register_index(0x00BF)] = 0x10000 - 9  # Battery Current, charging
    raw[register_index(0x00B7)] = 5462  # Battery Voltage (x0.01)
    return raw


def test_default_variant_keeps_documented_scaling():
    """Variant 0 must stay exactly as the protocol documents it.

    This is the scaling the smaller single-phase inverters use and what
    every existing installation is calibrated against, so it is pinned:
    no per-model work may silently move the default.
    """
    result = parse_raw(_raw_sample(), get_profile(DEFAULT_MOD))

    assert result["Total Load Power"] == pytest.approx(301)
    assert result["Load L1 Power"] == pytest.approx(301)
    assert result["Total Grid Power"] == pytest.approx(-432)
    assert result["External CT L1 Power"] == pytest.approx(-432)
    assert result["Battery Current"] == pytest.approx(-0.09)


def test_default_variant_matches_no_profile():
    """Passing no profile is the same as passing the default one."""
    raw = _raw_sample()
    assert parse_raw(raw) == parse_raw(raw, get_profile(DEFAULT_MOD))


def test_variant_two_scales_power_and_battery_current():
    """Variant 2: 10 W power units and 0.1 A battery current.

    Measured on a SUN-10K-SG02LP1-EU-AM3: with these ratios the
    instantaneous balance (load + export == inverter output) closes to
    ~0.1% and battery V x I reproduces Battery Power. With variant 0 the
    same registers read a tenth of the real values.
    """
    result = parse_raw(_raw_sample(), get_profile(2))

    assert result["Total Load Power"] == pytest.approx(3010)
    assert result["Load L1 Power"] == pytest.approx(3010)
    assert result["Total Grid Power"] == pytest.approx(-4320)
    assert result["External CT L1 Power"] == pytest.approx(-4320)
    assert result["Battery Current"] == pytest.approx(-0.9)
    # V x I must reproduce Battery Power
    assert result["Battery Voltage"] * result["Battery Current"] == pytest.approx(
        -49, abs=1
    )


def test_variant_one_scales_power_but_not_battery_current():
    """Variant 1 reports 10 W power units but battery current in 0.01 A."""
    result = parse_raw(_raw_sample(), get_profile(1))

    assert result["Total Load Power"] == pytest.approx(3010)
    assert result["Total Grid Power"] == pytest.approx(-4320)
    assert result["Battery Current"] == pytest.approx(-0.09)


def test_variant_only_changes_the_scaled_metrics():
    """Everything without a per-variant ratio must read the same."""
    raw = _raw_sample()
    scaled = {
        "Total Load Power",
        "Load L1 Power",
        "Load L2 Power",
        "Total Grid Power",
        "Internal CT L1 Power",
        "Internal CT L2 Power",
        "External CT L1 Power",
        "External CT L2 Power",
        "Battery Current",
    }

    default = parse_raw(raw, get_profile(DEFAULT_MOD))
    variant = parse_raw(raw, get_profile(2))

    assert default.keys() == variant.keys()
    assert {k: v for k, v in default.items() if k not in scaled} == {
        k: v for k, v in variant.items() if k not in scaled
    }


@pytest.mark.parametrize("mod", MOD_VARIANTS)
def test_every_variant_resolves_to_scalar_ratios(mod):
    """No per-variant list may survive into the parsing path.

    A list reaching float() is swallowed by the per-item error handling,
    which would drop the metric instead of failing loudly.
    """
    for section in iter_sections(get_profile(mod).definitions):
        for item in section.get("items", []):
            for key in ("ratio", "offset"):
                assert not isinstance(item.get(key), list), (item["titleEN"], key)


@pytest.mark.parametrize("mod", MOD_VARIANTS)
def test_every_variant_parses_all_metrics(mod):
    """Every variant must yield the same metrics as the default one."""
    raw = list(range(1, RAW_LEN + 1))
    assert parse_raw(raw, get_profile(mod)).keys() == parse_raw(raw).keys()


@pytest.mark.parametrize("mod", MOD_VARIANTS)
def test_entity_descriptions_are_variant_independent(mod):
    """Units and device classes must not depend on the variant."""
    assert build_descriptions(get_profile(mod)) == build_descriptions()


def test_ratio_lists_cover_the_known_variants():
    """Definitions carry one entry per variant wherever they carry a list."""
    lists = [
        item[key]
        for section in iter_sections(_RAW_DEFINITIONS)
        for item in section.get("items", [])
        for key in ("ratio", "offset")
        if isinstance(item.get(key), list)
    ]
    assert lists, "expected per-variant ratios in DYRealTime.txt"
    assert all(len(values) == len(MOD_VARIANTS) for values in lists)


def test_select_variant_passes_scalars_through():
    assert select_variant(0.1, 2) == 0.1
    assert select_variant([], 1) == []


def test_select_variant_reuses_last_entry_beyond_the_list():
    assert select_variant([1, 10], 5) == 10
    assert select_variant([1, 10], -1) == 10


def test_resolve_variant_does_not_mutate_the_source():
    before = [
        {"items": [{"titleEN": "X", "ratio": [1, 10, 10], "registers": ["0x00B2"]}]}
    ]
    resolved = resolve_variant(before, 2)

    assert before[0]["items"][0]["ratio"] == [1, 10, 10]
    assert resolved[0]["items"][0]["ratio"] == 10


def test_resolve_variant_skips_malformed_sections():
    assert resolve_variant(["not a section"], 1) == ["not a section"]


def test_get_profile_is_cached():
    assert get_profile(2) is get_profile(2)
    assert isinstance(get_profile(2), Profile)


def test_get_profile_falls_back_on_unknown_variant():
    assert get_profile(99).mod == DEFAULT_MOD
    assert get_profile(99).definitions is get_profile(DEFAULT_MOD).definitions


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (2, 2),
        ("2", 2),
        (None, DEFAULT_MOD),
        ("nonsense", DEFAULT_MOD),
        (7, DEFAULT_MOD),
        (-1, DEFAULT_MOD),
    ],
)
def test_normalize_mod(value, expected):
    assert normalize_mod(value) == expected
