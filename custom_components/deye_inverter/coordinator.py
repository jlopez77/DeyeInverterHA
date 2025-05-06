import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .InverterData import InverterData

_LOGGER = logging.getLogger(__name__)


class DeyeDataUpdateCoordinator(DataUpdateCoordinator[Dict[int, Any]]):
    """
    Coordinator asíncrono para datos del inversor.
    Ahora utiliza InverterData que requiere host, port y serial.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        serial: str,
        installed_power: float,
    ) -> None:
        # Inicializamos el cliente con host, puerto y serial
        self.inverter = InverterData(host, port, serial)

        # Exponemos estos atributos para que los sensores puedan usarlos
        self.serial = serial
        self.installed_power = installed_power

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[int, Any]:
        """
        Llamada periódica: obtiene los datos y maneja errores.
        """
        try:
            return await self.inverter.fetch_data()
        except Exception as err:
            _LOGGER.error("Error actualizando datos del inversor: %s", err)
            raise UpdateFailed(err)
