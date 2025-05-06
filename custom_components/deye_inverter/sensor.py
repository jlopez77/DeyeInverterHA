from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeyeDataUpdateCoordinator
from .InverterDataParser import _DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: Any, entry: Any, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator: DeyeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeyeInverterSensor(coordinator)], update_before_add=False)


class DeyeInverterSensor(CoordinatorEntity[DeyeDataUpdateCoordinator], SensorEntity):
    """Sensor that represents the total inverter power and all other values."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeyeDataUpdateCoordinator) -> None:
        """Initialize the sensor with coordinator and set metadata."""
        super().__init__(coordinator)
        serial = getattr(coordinator, "serial", "unknown")
        self._attr_name = f"Deye Inverter {serial}"
        self._attr_unique_id = f"deye_inverter_{serial}"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the Deye inverter."""
        serial = getattr(self.coordinator, "serial", "unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"Deye Inverter {serial}",
            manufacturer="Deye",
            model="Hybrid Inverter",
            sw_version="1.0.0",
        )

    @property
    def native_value(self) -> float:
        """Return the sum of PV1 and PV2 power as the main sensor value."""
        data = self.coordinator.data
        return float(data.get(0x00BA, 0.0) + data.get(0x00BB, 0.0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all other inverter parameters as state attributes."""
        attrs: dict[str, Any] = {}
        sections: Union[List[Any], Any] = (
            _DEFINITIONS.values() if isinstance(_DEFINITIONS, dict) else _DEFINITIONS
        )

        for section in sections:
            for item in section.get("items", []):
                title = item.get("titleEN") or item.get("titleZH") or "Unknown"
                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                    except (ValueError, TypeError):
                        continue
                    attrs[title] = self.coordinator.data.get(reg)

        attrs["attribution"] = "Data provided by Deye inverter via Modbus TCP"
        return attrs
