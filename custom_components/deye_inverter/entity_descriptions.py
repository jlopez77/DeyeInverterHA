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
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.util import slugify

from .const import REGISTER_BLOCKS
from .InverterDataParser import _DEFINITIONS, iter_sections
from .profiles import Profile

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
    "hz": {
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfFrequency.HERTZ,
    },
}


@dataclass(frozen=True, kw_only=True)
class DeyeSensorDescription(SensorEntityDescription):
    """Sensor description carrying the parser dict key for the metric."""

    metric_title: str = ""


def _registers_in_read_range(registers: Sequence[str]) -> bool:
    """True if every register of the item is covered by the read blocks."""
    if not registers:
        return False
    try:
        regs = [int(r, 16) for r in registers]
    except (TypeError, ValueError):
        return False
    return all(any(start <= r <= end for start, end in REGISTER_BLOCKS) for r in regs)


def build_descriptions(
    profile: Optional[Profile] = None,
) -> List[DeyeSensorDescription]:
    """Build one sensor description per usable DYRealTime.txt item.

    Entity metadata is variant-independent (only ratios differ), so the
    profile is accepted for consistency and future per-variant metrics.
    """
    definitions = profile.definitions if isinstance(profile, Profile) else _DEFINITIONS
    sections: Sequence[Dict[str, Any]] = iter_sections(definitions)

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

            # Unit-less metrics are statuses, device info, or bitfields; items
            # may also ask to be diagnostic while keeping their unit, for
            # device properties that never change (rated power).
            diagnostic = bool(item.get("diagnostic")) or meta is None
            category: Optional[EntityCategory] = (
                EntityCategory.DIAGNOSTIC if diagnostic else None
            )

            descriptions.append(
                DeyeSensorDescription(
                    key=slugify(title),
                    name=title,
                    metric_title=title,
                    device_class=meta["device_class"] if meta else None,
                    # Constant device properties are not worth recording
                    state_class=(
                        meta["state_class"]
                        if meta and not item.get("diagnostic")
                        else None
                    ),
                    native_unit_of_measurement=meta["unit"] if meta else None,
                    entity_category=category,
                )
            )

    return descriptions
