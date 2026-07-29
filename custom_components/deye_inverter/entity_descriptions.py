"""Derive per-metric sensor descriptions from the DYRealTime.txt definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.util import slugify

from .InverterDataParser import _DEFINITIONS

# Register blocks actually read by InverterData.fetch_data
_BLOCK1 = range(0x003B, 0x0070 + 1)
_BLOCK2 = range(0x0096, 0x00C3 + 1)

_UNIT_METADATA: Dict[str, Dict[str, Any]] = {
    "w": {
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "kwh": {
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "v": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricPotential.VOLT,
    },
    "a": {
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfElectricCurrent.AMPERE,
    },
    "%": {
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
    },
    "º": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
    },
}


@dataclass(frozen=True, kw_only=True)
class DeyeSensorDescription(SensorEntityDescription):
    """Sensor description carrying the parser dict key for the metric."""

    metric_title: str = ""


def _registers_in_read_range(registers: Sequence[str]) -> bool:
    """True if every register of the item is covered by the two read blocks."""
    if not registers:
        return False
    try:
        regs = [int(r, 16) for r in registers]
    except (TypeError, ValueError):
        return False
    return all(r in _BLOCK1 or r in _BLOCK2 for r in regs)


def build_descriptions() -> List[DeyeSensorDescription]:
    """Build one sensor description per usable DYRealTime.txt item."""
    sections: Sequence[Dict[str, Any]] = (
        list(_DEFINITIONS.values())
        if isinstance(_DEFINITIONS, dict)
        else _DEFINITIONS  # type: ignore[assignment]
    )

    descriptions: List[DeyeSensorDescription] = []
    seen: set[str] = set()

    for section in sections:
        for item in section.get("items", []):
            title = item.get("titleEN")
            if not title or title in seen:
                continue
            if not _registers_in_read_range(item.get("registers", [])):
                continue
            seen.add(title)

            unit = str(item.get("unit") or "").strip().lower()
            meta = _UNIT_METADATA.get(unit)

            is_text = meta is None
            category: Optional[EntityCategory] = None
            if is_text and (
                item.get("interactionType") == 2 or item.get("parserRule") == 6
            ):
                category = EntityCategory.DIAGNOSTIC

            descriptions.append(
                DeyeSensorDescription(
                    key=slugify(title),
                    name=title,
                    metric_title=title,
                    device_class=meta["device_class"] if meta else None,
                    state_class=meta["state_class"] if meta else None,
                    native_unit_of_measurement=meta["unit"] if meta else None,
                    entity_category=category,
                )
            )

    return descriptions
