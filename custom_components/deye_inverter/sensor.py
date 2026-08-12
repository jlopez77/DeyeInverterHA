from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeyeDataUpdateCoordinator
from .entity_descriptions import DeyeSensorDescription, build_descriptions

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by Deye inverter via Modbus TCP"


def _inverter_device_info(coordinator: DeyeDataUpdateCoordinator) -> DeviceInfo:
    """Device info shared by all entities of one inverter."""
    serial = getattr(coordinator, "serial", "unknown")
    return DeviceInfo(
        identifiers={(DOMAIN, serial)},
        name=f"Deye Inverter {serial}",
        manufacturer="Deye",
        model="Hybrid Inverter",
        sw_version="1.0.0",
    )


async def async_setup_entry(
    hass: Any, entry: Any, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator: DeyeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [DeyeInverterSensor(coordinator)]
    if getattr(coordinator, "installed_power", 0):
        entities.append(DeyeProductionPercentSensor(coordinator))
    entities.extend(
        DeyeMetricSensor(coordinator, description)
        for description in build_descriptions()
    )
    async_add_entities(entities, update_before_add=False)


class DeyeInverterSensor(CoordinatorEntity[DeyeDataUpdateCoordinator], SensorEntity):
    """Legacy aggregate sensor: total PV power (PV1 + PV2)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeyeDataUpdateCoordinator) -> None:
        """Initialize the sensor with coordinator and set metadata."""
        super().__init__(coordinator)
        serial = getattr(coordinator, "serial", "unknown")
        self._attr_unique_id = f"deye_inverter_{serial}"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the Deye inverter."""
        return _inverter_device_info(self.coordinator)

    @property
    def native_value(self) -> float:
        """Return the sum of PV1 and PV2 power as the main sensor value."""
        data = self.coordinator.data
        try:
            return float(data.get("PV1 Power", 0.0)) + float(data.get("PV2 Power", 0.0))
        except (TypeError, ValueError):
            return 0.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the attribution only; metrics are dedicated entities now."""
        return {"attribution": ATTRIBUTION}


class DeyeProductionPercentSensor(
    CoordinatorEntity[DeyeDataUpdateCoordinator], SensorEntity
):
    """Current PV production as a percentage of the installed power."""

    _attr_has_entity_name = True
    _attr_name = "Production"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:solar-power-variant"

    def __init__(self, coordinator: DeyeDataUpdateCoordinator) -> None:
        """Initialize the sensor with coordinator and set metadata."""
        super().__init__(coordinator)
        serial = getattr(coordinator, "serial", "unknown")
        self._attr_unique_id = f"{serial}_production_percent"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the Deye inverter."""
        return _inverter_device_info(self.coordinator)

    @property
    def native_value(self) -> Optional[float]:
        """Return PV1+PV2 power relative to the installed power in kW."""
        installed_kw = getattr(self.coordinator, "installed_power", 0)
        try:
            installed_w = float(installed_kw) * 1000
        except (TypeError, ValueError):
            return None
        if installed_w <= 0:
            return None

        data = self.coordinator.data or {}
        try:
            pv_power = float(data.get("PV1 Power", 0.0)) + float(
                data.get("PV2 Power", 0.0)
            )
        except (TypeError, ValueError):
            return None
        return round(pv_power / installed_w * 100, 1)


class DeyeMetricSensor(CoordinatorEntity[DeyeDataUpdateCoordinator], SensorEntity):
    """One sensor per inverter metric defined in DYRealTime.txt."""

    _attr_has_entity_name = True
    entity_description: DeyeSensorDescription

    def __init__(
        self,
        coordinator: DeyeDataUpdateCoordinator,
        description: DeyeSensorDescription,
    ) -> None:
        """Initialize the metric sensor from its description."""
        super().__init__(coordinator)
        self.entity_description = description
        serial = getattr(coordinator, "serial", "unknown")
        self._attr_unique_id = f"{serial}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the Deye inverter."""
        return _inverter_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        """Available only when the metric is present in the coordinator data."""
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return self.entity_description.metric_title in data

    @property
    def native_value(self) -> Optional[Any]:
        """Return the parsed value for this metric, or None if missing."""
        data = self.coordinator.data or {}
        return data.get(self.entity_description.metric_title)
