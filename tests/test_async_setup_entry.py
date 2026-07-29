import pytest
from unittest.mock import MagicMock

from custom_components.deye_inverter.sensor import (
    DeyeInverterSensor,
    DeyeMetricSensor,
    DeyeProductionPercentSensor,
    async_setup_entry,
)
from custom_components.deye_inverter.entity_descriptions import build_descriptions
from custom_components.deye_inverter.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry_adds_entities():
    """Setup adds the aggregate sensor plus one entity per metric description."""
    hass = MagicMock()
    added = []

    def async_add_entities(entities, update_before_add: bool = True):
        added.extend(entities)

    mock_coordinator = MagicMock()
    mock_coordinator.serial = "ABC123"
    mock_coordinator.installed_power = 5
    hass.data = {
        DOMAIN: {
            "mock_entry_id": mock_coordinator
        }
    }

    mock_entry = MagicMock()
    mock_entry.entry_id = "mock_entry_id"

    await async_setup_entry(hass, mock_entry, async_add_entities)

    assert len(added) == 2 + len(build_descriptions())
    assert isinstance(added[0], DeyeInverterSensor)
    assert isinstance(added[1], DeyeProductionPercentSensor)
    assert all(isinstance(e, DeyeMetricSensor) for e in added[2:])
