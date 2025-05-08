import pytest
from unittest.mock import MagicMock, patch

from custom_components.deye_inverter.sensor import async_setup_entry
from custom_components.deye_inverter.const import DOMAIN


@pytest.mark.asyncio
@patch("custom_components.deye_inverter.sensor.DeyeInverterSensor")
async def test_async_setup_entry_adds_entity(mock_sensor_class):
    """Test that async_setup_entry adds DeyeInverterSensor correctly."""
    # Mock Home Assistant and its internal structures
    hass = MagicMock()

    # Define a no-op async function to avoid warnings
    async def async_add_entities(entities, update_before_add: bool = True):
        pass

    # Create mock coordinator and inject into hass.data
    mock_coordinator = MagicMock()
    hass.data = {
        DOMAIN: {
            "mock_entry_id": mock_coordinator
        }
    }

    # Mock config entry
    mock_entry = MagicMock()
    mock_entry.entry_id = "mock_entry_id"

    # Run the setup
    await async_setup_entry(hass, mock_entry, async_add_entities)

    # Verify that the sensor was added
    mock_sensor_class.assert_called_once_with(mock_coordinator)
