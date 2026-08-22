"""Tests for the third and fourth PV string and the PV aggregates."""

from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.deye_inverter.const import REGISTER_BLOCKS
from custom_components.deye_inverter.entity_descriptions import build_descriptions
from custom_components.deye_inverter.InverterDataParser import parse_raw, register_index
from custom_components.deye_inverter.sensor import (
    DeyeInverterSensor,
    DeyeProductionPercentSensor,
    _detected_mppts,
    total_pv_power,
)

RAW_LEN = sum(end - start + 1 for start, end in REGISTER_BLOCKS)

PV_TITLES = (
    "PV3 Power",
    "PV3 Voltage",
    "PV3 Current",
    "PV4 Power",
    "PV4 Voltage",
    "PV4 Current",
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.serial = "ABC123"
    coordinator.installed_power = 10
    coordinator.data = {}
    return coordinator


def test_third_string_is_parsed():
    """Values read from a real 3-MPPT inverter (0x0071/0x0072/0x00BC)."""
    raw = [0] * RAW_LEN
    raw[register_index(0x0071)] = 79
    raw[register_index(0x0072)] = 2
    raw[register_index(0x00BC)] = 1

    result = parse_raw(raw)

    assert result["PV3 Voltage"] == pytest.approx(7.9)
    assert result["PV3 Current"] == pytest.approx(0.2)
    assert result["PV3 Power"] == pytest.approx(1)


def test_fourth_string_is_parsed():
    raw = [0] * RAW_LEN
    raw[register_index(0x0073)] = 3801
    raw[register_index(0x0074)] = 15
    raw[register_index(0x00BD)] = 570

    result = parse_raw(raw)

    assert result["PV4 Voltage"] == pytest.approx(380.1)
    assert result["PV4 Current"] == pytest.approx(1.5)
    assert result["PV4 Power"] == pytest.approx(570)


def test_extending_the_block_did_not_move_the_other_registers():
    """The later blocks must still line up after the PV extension."""
    raw = list(range(1, RAW_LEN + 1))
    result = parse_raw(raw)

    # A register from each block still resolves to a distinct known value
    assert result["PV1 Voltage"] == pytest.approx(raw[register_index(0x006D)] * 0.1)
    assert result["Battery SOC"] == pytest.approx(raw[register_index(0x00B8)])
    assert result["Control Board Version No."] == pytest.approx(
        raw[register_index(0x000D)]
    )
    assert result["Device Phases"] == pytest.approx(
        raw[register_index(0x0012)] & 0x000F
    )


@pytest.mark.parametrize(
    "mppts,expected",
    [
        (2, set()),
        (3, {"PV3 Power", "PV3 Voltage", "PV3 Current"}),
        (4, set(PV_TITLES)),
        (None, set(PV_TITLES)),
    ],
)
def test_string_entities_follow_the_mppt_count(mppts, expected):
    """A 2-string inverter must not get PV3/PV4 entities stuck at zero."""
    titles = {d.metric_title for d in build_descriptions(None, mppts)}
    assert titles & set(PV_TITLES) == expected
    # The always-present strings are never gated
    assert {"PV1 Power", "PV2 Power"} <= titles


def test_unknown_mppt_count_keeps_every_string():
    """Detection failures must not hide data an inverter does report."""
    assert build_descriptions(None, None) == build_descriptions()


def test_total_pv_power_sums_every_string():
    data = {
        "PV1 Power": 432.0,
        "PV2 Power": 451.0,
        "PV3 Power": 1.0,
        "PV4 Power": 570.0,
    }
    assert total_pv_power(data) == pytest.approx(1454.0)


def test_total_pv_power_ignores_missing_strings():
    assert total_pv_power({"PV1 Power": 100.0, "PV2 Power": 50.0}) == pytest.approx(150)
    assert total_pv_power({}) == pytest.approx(0)
    assert total_pv_power(None) == pytest.approx(0)


def test_total_pv_power_is_unknown_on_unusable_values():
    """A present but unparseable value must not read as a lower total."""
    assert total_pv_power({"PV1 Power": 100.0, "PV2 Power": "bad"}) is None


def test_aggregate_sensor_includes_the_third_string(mock_coordinator):
    """The legacy sensor used to report PV1+PV2 only, losing PV3."""
    mock_coordinator.data = {
        "PV1 Power": 432.0,
        "PV2 Power": 451.0,
        "PV3 Power": 117.0,
    }
    assert DeyeInverterSensor(mock_coordinator).native_value == pytest.approx(1000.0)


def test_aggregate_sensor_keeps_its_unique_id(mock_coordinator):
    """Existing installations must keep their entity and its history."""
    assert DeyeInverterSensor(mock_coordinator).unique_id == "deye_inverter_ABC123"


def test_production_percent_uses_every_string(mock_coordinator):
    """10 kW installed, 1 kW across three strings -> 10 %."""
    mock_coordinator.data = {
        "PV1 Power": 432.0,
        "PV2 Power": 451.0,
        "PV3 Power": 117.0,
    }
    assert DeyeProductionPercentSensor(mock_coordinator).native_value == pytest.approx(
        10.0
    )


@pytest.mark.parametrize(
    "reported,expected",
    [
        (3.0, 3),
        (3, 3),
        ("3", 3),
        (4.0, 4),
        (0.0, None),  # register present but empty
        (9.0, None),  # more strings than the definitions cover
        (None, None),
        ("nonsense", None),
    ],
)
def test_detected_mppts(mock_coordinator, reported, expected):
    mock_coordinator.data = {"Device MPPTs": reported}
    assert _detected_mppts(mock_coordinator) == expected


def test_detected_mppts_without_data(mock_coordinator):
    """A coordinator that has not refreshed yet detects nothing."""
    mock_coordinator.data = None
    assert _detected_mppts(mock_coordinator) is None
