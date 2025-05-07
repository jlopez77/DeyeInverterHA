import pytest
from unittest.mock import MagicMock

from custom_components.deye_inverter.sensor import DeyeInverterSensor
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = {
        "PV1 Power": 500,
        "PV2 Power": 300,
        "Battery Power": 100,
    }
    coordinator.serial = "ABC123"
    coordinator.last_update_success = True
    return coordinator

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
    """Test that extra attributes are populated."""
    mock_coordinator.data = {
        "Battery Power": 100,
        "attribution": "Data provided by Deye inverter via Modbus TCP"
    }
    sensor = DeyeInverterSensor(mock_coordinator)
    attrs = sensor.extra_state_attributes

    assert isinstance(attrs, dict)
    assert "Battery Power" in attrs
    assert attrs["Battery Power"] == 100

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
