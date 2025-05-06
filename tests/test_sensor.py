import pytest
from unittest.mock import MagicMock, patch

from custom_components.deye_inverter.sensor import DeyeInverterSensor
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = {
        0x00BA: 500,   # PV1 power
        0x00BB: 300,   # PV2 power
        0x00BC: 100,   # Battery power
    }
    coordinator.serial = "ABC123"
    coordinator.last_update_success = True
    return coordinator

def test_sensor_properties(mock_coordinator):
    """Test core sensor properties like name, unique_id, native_value."""
    sensor = DeyeInverterSensor(mock_coordinator)

    assert sensor.name == "Deye Inverter ABC123"
    assert sensor.unique_id == "deye_inverter_ABC123"
    assert sensor.native_value == 800
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.should_poll is False
    assert sensor.available is True

@patch("custom_components.deye_inverter.sensor._DEFINITIONS", [
    {
        "items": [
            {
                "titleEN": "Battery Power",
                "registers": ["00BC"],
            }
        ]
    }
])
def test_extra_state_attributes(mock_coordinator):
    """Test that extra attributes are populated."""
    sensor = DeyeInverterSensor(mock_coordinator)
    attrs = sensor.extra_state_attributes

    assert isinstance(attrs, dict)
    assert "Battery Power" in attrs
    assert attrs["Battery Power"] == 100

def test_device_info(mock_coordinator):
    """Test that device_info is returned correctly."""
    sensor = DeyeInverterSensor(mock_coordinator)
    info = sensor.device_info

    assert isinstance(info, dict)
    assert info["identifiers"] == {("deye_inverter", "ABC123")}
    assert info["manufacturer"] == "Deye"
    assert info["name"] == "Deye Inverter ABC123"
    assert info["model"] == "Hybrid Inverter"
