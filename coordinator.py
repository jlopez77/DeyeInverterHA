"""DataUpdateCoordinator para Deye Inverter."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL
from .InverterData import InverterData

_LOGGER = logging.getLogger(__name__)


class DeyeDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinador que consulta periódicamente el inversor."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        serial: str,
        installed_power: int,
    ):
        """Inicializa el coordinador y guarda los parámetros."""
        # Guarda el serial para usarlo luego en las entidades
        self.serial = serial
        # (Opcional) también puedes guardar host/port si los necesitas:
        self.host = host
        self.port = port
        self.installed_power = installed_power

        # Inicializa el cliente Modbus
        self.client = InverterData(host, port, serial, installed_power)

        super().__init__(
            hass,
            _LOGGER,
            name=f"DeyeInverter-{serial}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        """
        Llamada periódica para obtener datos del inversor.

        - En un fallo de lectura, si ya teníamos datos previos (self.data es dict),
          los devolvemos para evitar que las entidades desaparezcan.
        - Si es el primer fetch y falla, devolvemos {} para que self.data sea un dict vacío.
        """
        try:
            new_data = await self.hass.async_add_executor_job(
                self.client.read_real_time
            )
            return new_data or {}
        except Exception as err:
            _LOGGER.error("Error al leer inversor, manteniendo últimos datos: %s", err)
            return self.data if isinstance(self.data, dict) else {}
