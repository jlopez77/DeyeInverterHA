import pytest
from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.deye_inverter.entity_descriptions import build_descriptions
from custom_components.deye_inverter.sensor import (
    DeyeInverterSensor,
    DeyeMetricSensor,
    DeyeProductionPercentSensor,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "PV1 Power": 500,
        "PV2 Power": 300,
        "Battery Power": 100,
    }
    coordinator.serial = "ABC123"
    coordinator.installed_power = 5
    coordinator.last_update_success = True
    return coordinator


def _description(title):
    matches = [d for d in build_descriptions() if d.metric_title == title]
    assert matches, f"No description generated for {title!r}"
    return matches[0]


# === Aggregate sensor ===

def test_sensor_properties(mock_coordinator):
    """Test core sensor properties like name, unique_id, native_value."""
    sensor = DeyeInverterSensor(mock_coordinator)

    assert sensor.device_info["name"] == "Deye Inverter ABC123"
    assert sensor.unique_id == "deye_inverter_ABC123"
    assert sensor.native_value == 800
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.should_poll is False
    assert sensor.available is True

def test_extra_state_attributes(mock_coordinator):
    """The aggregate sensor exposes only the attribution, no metrics."""
    sensor = DeyeInverterSensor(mock_coordinator)
    attrs = sensor.extra_state_attributes

    assert attrs == {"attribution": "Data provided by Deye inverter via Modbus TCP"}

def test_device_info(mock_coordinator):
    """Test that device_info is returned correctly."""
    sensor = DeyeInverterSensor(mock_coordinator)
    info = sensor.device_info

    assert info is not None, "device_info is None — ensure the sensor defines the property"
    assert isinstance(info, dict)
    assert info["identifiers"] == {("deye_inverter", "ABC123")}
    assert info["manufacturer"] == "Deye"
    assert info["name"] == "Deye Inverter ABC123"
    assert info["model"] == "Hybrid Inverter"

def test_native_value_fallback():
    """Ensure native_value returns 0.0 on bad data."""
    coordinator = MagicMock()
    coordinator.data = {
        "PV1 Power": "bad",
        "PV2 Power": None,
    }
    coordinator.serial = "TEST_FAIL"
    sensor = DeyeInverterSensor(coordinator)

    assert sensor.native_value == 0.0


# === Production percent sensor ===

def test_production_percent_value(mock_coordinator):
    """PV1+PV2 relative to installed power in kW."""
    sensor = DeyeProductionPercentSensor(mock_coordinator)

    # (500 + 300) W of 5 kW installed -> 16.0 %
    assert sensor.native_value == 16.0
    assert sensor.native_unit_of_measurement == "%"
    assert sensor.unique_id == "ABC123_production_percent"

def test_production_percent_no_installed_power(mock_coordinator):
    """Without a usable installed power the sensor reports None."""
    mock_coordinator.installed_power = 0
    assert DeyeProductionPercentSensor(mock_coordinator).native_value is None

    mock_coordinator.installed_power = "bad"
    assert DeyeProductionPercentSensor(mock_coordinator).native_value is None

def test_production_percent_bad_data(mock_coordinator):
    """Bad PV values report None instead of raising."""
    mock_coordinator.data = {"PV1 Power": "bad"}
    assert DeyeProductionPercentSensor(mock_coordinator).native_value is None


# === Description builder ===

def test_build_descriptions_covers_readable_metrics():
    """All metrics within the read register blocks get a description."""
    descriptions = build_descriptions()
    titles = {d.metric_title for d in descriptions}

    assert len(descriptions) >= 40
    assert "PV1 Power" in titles
    assert "Total Grid Production" in titles
    assert "Battery Status" in titles
    assert "Alert" in titles

def test_build_descriptions_covers_device_info_metrics():
    """Metrics in the optional read blocks (device info, work mode) exist."""
    descriptions = {d.metric_title: d for d in build_descriptions()}

    for title in (
        "Inverter ID",
        "Communication Board Version No.",
        "Control Board Version No.",
        "Work Mode",
        "Time of use",
    ):
        assert title in descriptions
        assert descriptions[title].entity_category is EntityCategory.DIAGNOSTIC


def test_registers_outside_read_blocks_are_skipped():
    """An item whose registers are not covered by any read block is excluded."""
    from custom_components.deye_inverter.entity_descriptions import (
        _registers_in_read_range,
    )

    assert _registers_in_read_range(["0x003B"]) is True
    assert _registers_in_read_range(["0xFFFF"]) is False
    assert _registers_in_read_range(["0x003B", "0xFFFF"]) is False
    assert _registers_in_read_range([]) is False

def test_description_metadata_power():
    desc = _description("PV1 Power")
    assert desc.device_class is SensorDeviceClass.POWER
    assert desc.state_class is SensorStateClass.MEASUREMENT
    assert desc.native_unit_of_measurement == "W"

def test_description_metadata_energy():
    desc = _description("Total Grid Production")
    assert desc.device_class is SensorDeviceClass.ENERGY
    assert desc.state_class is SensorStateClass.TOTAL_INCREASING
    assert desc.native_unit_of_measurement == "kWh"

def test_description_metadata_temperature():
    desc = _description("Battery Temperature")
    assert desc.device_class is SensorDeviceClass.TEMPERATURE
    assert desc.native_unit_of_measurement == "°C"

def test_description_metadata_battery_soc():
    desc = _description("Battery SOC")
    assert desc.device_class is SensorDeviceClass.BATTERY
    assert desc.native_unit_of_measurement == "%"

def test_description_metadata_status_is_diagnostic_text():
    """Status/enum metrics are plain text diagnostic sensors."""
    for title in ("Battery Status", "Alert"):
        desc = _description(title)
        assert desc.device_class is None
        assert desc.state_class is None
        assert desc.native_unit_of_measurement is None
        assert desc.entity_category is EntityCategory.DIAGNOSTIC

def test_description_unique_keys():
    keys = [d.key for d in build_descriptions()]
    assert len(keys) == len(set(keys))


# === Per-metric sensor ===

def test_metric_sensor_value_and_unique_id(mock_coordinator):
    sensor = DeyeMetricSensor(mock_coordinator, _description("PV1 Power"))

    assert sensor.unique_id == "ABC123_pv1_power"
    assert sensor.native_value == 500
    assert sensor.available is True
    assert sensor.device_info["identifiers"] == {("deye_inverter", "ABC123")}

def test_metric_sensor_missing_value_unavailable(mock_coordinator):
    sensor = DeyeMetricSensor(mock_coordinator, _description("Battery SOC"))

    assert sensor.native_value is None
    assert sensor.available is False

def test_metric_sensor_handles_none_data(mock_coordinator):
    mock_coordinator.data = None
    sensor = DeyeMetricSensor(mock_coordinator, _description("PV1 Power"))

    assert sensor.native_value is None
    assert sensor.available is False
