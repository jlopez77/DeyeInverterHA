"""Platform de sensor para Deye Inverter.

Presenta un único sensor con valor principal (Total PV Power)
y expone el resto de registros como atributos.
"""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

# from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeyeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Definición de todos los registros tal como en DYRealTime.txt
# (la clave es el identificador interno; 'address' es la dirección Modbus)
SENSOR_REGISTERS = {
    # Solar
    "PV1_Power": {"address": 0x00BA, "name": "PV1 Power", "unit": "W"},
    "PV2_Power": {"address": 0x00BB, "name": "PV2 Power", "unit": "W"},
    # Battery
    "Battery_Status": {"address": 0x00BE, "name": "Battery Status", "unit": ""},
    "Battery_Power": {"address": 0x00BE, "name": "Battery Power", "unit": "W"},
    "Battery_Voltage": {"address": 0x00B7, "name": "Battery Voltage", "unit": "V"},
    "Battery_SOC": {"address": 0x00B8, "name": "Battery SOC", "unit": "%"},
    "Battery_Current": {"address": 0x00BF, "name": "Battery Current", "unit": "A"},
    "Battery_Temperature": {
        "address": 0x00B6,
        "name": "Battery Temperature",
        "unit": "º",
    },
    # Grid
    "Grid_Status": {"address": 0x00A9, "name": "Grid Status", "unit": ""},
    "Total_Grid_Power": {"address": 0x00A9, "name": "Total Grid Power", "unit": "W"},
    "Grid_Voltage_L1": {"address": 0x0096, "name": "Grid Voltage L1", "unit": "V"},
    "Grid_Voltage_L2": {"address": 0x0097, "name": "Grid Voltage L2", "unit": "V"},
    # Load (Upsload)
    "Total_Load_Power": {"address": 0x00B2, "name": "Total Load Power", "unit": "W"},
    "Load_L1_Power": {"address": 0x00B0, "name": "Load L1 Power", "unit": "W"},
    "Load_L2_Power": {"address": 0x00B1, "name": "Load L2 Power", "unit": "W"},
    "Load_Voltage": {"address": 0x009D, "name": "Load Voltage", "unit": "V"},
    # Inverter
    "Running_Status": {"address": 0x003B, "name": "Running Status", "unit": ""},
    "Total_Power": {"address": 0x00AF, "name": "Total Power", "unit": "W"},
    "Current_L1": {"address": 0x00A4, "name": "Current L1", "unit": "A"},
    "Current_L2": {"address": 0x00A5, "name": "Current L2", "unit": "A"},
    "Inverter_L1_Power": {"address": 0x00AD, "name": "Inverter L1 Power", "unit": "W"},
    "Inverter_L2_Power": {"address": 0x00AE, "name": "Inverter L2 Power", "unit": "W"},
    "DC_Temperature": {"address": 0x005A, "name": "DC Temperature", "unit": "º"},
    "AC_Temperature": {"address": 0x005B, "name": "AC Temperature", "unit": "º"},
    # Alert
    "Alert": {"address": 0x0065, "name": "Alert", "unit": ""},
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Configura el sensor único tras la creación de la config entry."""
    coordinator: DeyeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeyeInverterSensor(coordinator)], True)


class DeyeInverterSensor(CoordinatorEntity, SensorEntity):
    """Un único sensor que expone Total PV Power como estado y el resto como atributos."""

    def __init__(self, coordinator: DeyeDataUpdateCoordinator):
        """Inicializa el sensor y lo suscribe al coordinador."""
        super().__init__(coordinator)
        self._attr_name = "Deye Inverter Power"
        self._attr_unique_id = f"{coordinator.serial}_inverter_power"
        self._attr_native_unit_of_measurement = "W"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._pv1_addr = SENSOR_REGISTERS["PV1_Power"]["address"]
        self._pv2_addr = SENSOR_REGISTERS["PV2_Power"]["address"]

    @property
    def native_value(self):
        """El valor principal es la suma de PV1 + PV2."""
        pv1 = self.coordinator.data.get(self._pv1_addr, 0) or 0
        pv2 = self.coordinator.data.get(self._pv2_addr, 0) or 0
        return round(pv1 + pv2, 2)

    @property
    def extra_state_attributes(self) -> dict:
        """Expone todos los demás registros como atributos del sensor."""
        attrs: dict[str, float] = {}
        for key, meta in SENSOR_REGISTERS.items():
            addr = meta["address"]
            # Saltamos los PV1 y PV2, ya usados en el estado principal
            if addr in (self._pv1_addr, self._pv2_addr):
                continue
            value = self.coordinator.data.get(addr)
            attrs[meta["name"]] = value
        return attrs

    @property
    def available(self) -> bool:
        """Disponible si la última lectura fue exitosa."""
        return self.coordinator.last_update_success
