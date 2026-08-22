"""Tests for reading what the inverter reports about itself."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.deye_inverter.config_flow import MOD_AUTO, _resolve_mod
from custom_components.deye_inverter.const import (
    DEFAULT_MOD,
    REGISTER_BLOCKS,
    TEN_WATT_UNITS_FROM_RATED_POWER,
)
from custom_components.deye_inverter.entity_descriptions import build_descriptions
from custom_components.deye_inverter import InverterData as inverter_data
from custom_components.deye_inverter.InverterData import DeviceCapabilities
from custom_components.deye_inverter.InverterDataParser import parse_raw, register_index
from custom_components.deye_inverter.profiles import suggest_mod

# Values read from a real SUN-10K-SG02LP1-EU-AM3
RATED_POWER_LOW = 0x86A0
RATED_POWER_HIGH = 0x0001
COUNTS_3MPPT_1PHASE = 0x0301

RAW_LEN = sum(end - start + 1 for start, end in REGISTER_BLOCKS)


def _raw_with_capabilities():
    raw = [0] * RAW_LEN
    raw[register_index(0x0010)] = RATED_POWER_LOW
    raw[register_index(0x0011)] = RATED_POWER_HIGH
    raw[register_index(0x0012)] = COUNTS_3MPPT_1PHASE
    return raw


def test_rated_power_is_a_32_bit_value_low_word_first():
    """0x86A0 0x0001 is 10 kW, not 225 MW: the low word comes first."""
    result = parse_raw(_raw_with_capabilities())
    assert result["Device Rated Power"] == pytest.approx(10000.0)


def test_counts_are_unpacked_from_one_register():
    """0x0012 packs the MPPT count and the phase count into one word."""
    result = parse_raw(_raw_with_capabilities())
    assert result["Device MPPTs"] == pytest.approx(3)
    assert result["Device Phases"] == pytest.approx(1)


def test_capability_metrics_are_dropped_when_their_block_is_missing():
    """A raw list without the capability block must not invent values."""
    raw = [0] * (RAW_LEN - 3)
    result = parse_raw(raw)
    for title in ("Device Rated Power", "Device MPPTs", "Device Phases"):
        assert title not in result


def test_partial_multi_register_value_is_dropped():
    """Half of a 32-bit value would parse as a plausible wrong number."""
    raw = [0] * (register_index(0x0011))  # 0x0010 readable, 0x0011 is not
    raw[register_index(0x0010)] = RATED_POWER_LOW
    assert "Device Rated Power" not in parse_raw(raw)


def test_rated_power_is_a_diagnostic_without_statistics():
    """A constant device property should not be recorded as a measurement."""
    by_title = {d.metric_title: d for d in build_descriptions()}

    rated = by_title["Device Rated Power"]
    assert rated.entity_category == "diagnostic"
    assert rated.native_unit_of_measurement == "W"
    assert rated.device_class == "power"
    assert rated.state_class is None

    # Unit-less counts stay plain diagnostic text
    assert by_title["Device MPPTs"].entity_category == "diagnostic"
    assert by_title["Device MPPTs"].device_class is None


@pytest.mark.parametrize(
    "rated_power,expected",
    [
        (10000.0, 2),
        (12000.0, 2),
        (TEN_WATT_UNITS_FROM_RATED_POWER, 2),
        (8000.0, DEFAULT_MOD),
        (5000.0, DEFAULT_MOD),
        (0, DEFAULT_MOD),
        (None, DEFAULT_MOD),
        ("nonsense", DEFAULT_MOD),
    ],
)
def test_suggest_mod(rated_power, expected):
    assert suggest_mod(rated_power) == expected


def test_resolve_mod_prefers_an_explicit_choice():
    """An explicit variant is never overridden by detection."""
    caps = DeviceCapabilities(rated_power=10000.0)
    assert _resolve_mod("0", caps) == 0
    assert _resolve_mod("1", caps) == 1


def test_resolve_mod_detects_from_rated_power():
    assert _resolve_mod(MOD_AUTO, DeviceCapabilities(rated_power=10000.0)) == 2
    assert _resolve_mod(MOD_AUTO, DeviceCapabilities(rated_power=5000.0)) == DEFAULT_MOD


def test_resolve_mod_falls_back_without_detection():
    """Devices that do not expose the register keep the documented scaling."""
    assert _resolve_mod(MOD_AUTO, DeviceCapabilities()) == DEFAULT_MOD
    assert _resolve_mod(MOD_AUTO, None) == DEFAULT_MOD
    assert _resolve_mod(MOD_AUTO, MagicMock()) == DEFAULT_MOD


def test_test_connection_reports_capabilities():
    """The connection test doubles as the capability probe."""
    modbus = MagicMock()
    modbus.read_holding_registers.side_effect = [
        [0],  # the liveness read
        [RATED_POWER_LOW, RATED_POWER_HIGH, COUNTS_3MPPT_1PHASE],
    ]

    with patch(
        "custom_components.deye_inverter.InverterData.PySolarmanV5",
        return_value=modbus,
    ):
        caps = inverter_data.test_connection("192.168.1.100", 8899, "1131691043")

    assert caps == DeviceCapabilities(rated_power=10000.0, mppts=3, phases=1)
    modbus.disconnect.assert_called_once()


def test_test_connection_survives_missing_capability_registers():
    """Devices that reject the block still pass the connection test."""
    modbus = MagicMock()
    modbus.read_holding_registers.side_effect = [
        [0],
        RuntimeError("illegal data address"),
    ]

    with patch(
        "custom_components.deye_inverter.InverterData.PySolarmanV5",
        return_value=modbus,
    ):
        caps = inverter_data.test_connection("192.168.1.100", 8899, "1131691043")

    assert caps == DeviceCapabilities()


def test_test_connection_ignores_unpopulated_counts():
    """0x0012 below 0x0101 carries no counts yet."""
    modbus = MagicMock()
    modbus.read_holding_registers.side_effect = [[0], [0, 0, 0]]

    with patch(
        "custom_components.deye_inverter.InverterData.PySolarmanV5",
        return_value=modbus,
    ):
        caps = inverter_data.test_connection("192.168.1.100", 8899, "1131691043")

    assert caps.mppts is None
    assert caps.phases is None
    assert caps.rated_power is None


def test_test_connection_still_raises_on_a_dead_connection():
    modbus = MagicMock()
    modbus.read_holding_registers.side_effect = OSError("no route")

    with patch(
        "custom_components.deye_inverter.InverterData.PySolarmanV5",
        return_value=modbus,
    ):
        with pytest.raises(OSError):
            inverter_data.test_connection("192.168.1.100", 8899, "1131691043")
