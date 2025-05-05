import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .InverterDataParser import _DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeyeInverterSensor(coordinator)], update_before_add=False)


class DeyeInverterSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Deye Inverter"
        self._attr_unique_id = f"{coordinator.serial}_inverter"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Total power: PV1 + PV2"""
        data = self.coordinator.data or {}
        pv1 = data.get(0x00BA, 0)
        pv2 = data.get(0x00BB, 0)
        total = pv1 + pv2
        return round(total, 2)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        attrs = {}
        sections = (
            _DEFINITIONS.values() if isinstance(_DEFINITIONS, dict) else _DEFINITIONS
        )
        for section in sections:
            for item in section.get("items", []):
                title = item.get("titleEN") or item.get("title")
                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                    except (ValueError, TypeError):
                        continue
                    raw_val = data.get(reg)
                    if raw_val is None:
                        continue
                    attrs[title] = raw_val
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this inverter."""
        return {
            "identifiers": {
                (DOMAIN, self.coordinator.serial)  # type: ignore[attr-defined]
            },  
            "name": "Deye Inverter",
            "manufacturer": "Deye",
            "model": "Inverter",
            "sw_version": "1.0.0",
        } 
