import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .InverterData import InverterData

_LOGGER = logging.getLogger(__name__)


class DeyeDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """
    Asynchronous coordinator for inverter data.
    Uses InverterData which requires host, port, and serial.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        installed_power: float,
    ) -> None:
        host = config_entry.data["host"]
        port = config_entry.data.get("port", 8899)
        serial = config_entry.data["serial"]

        self.inverter = InverterData(
            host=host,
            port=port,
            serial=serial,
            hass=hass,
            config_entry=config_entry,
        )
        self.serial = serial
        self.installed_power = installed_power
        self._last_known_data: Dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """
        Periodic call: fetch data and handle errors.
        Returns last known data on failure to avoid sensor 'unavailable'.
        """
        try:
            data = await self.inverter.fetch_data()
            self._last_known_data = data
            return data
        except Exception as err:
            _LOGGER.warning("Modbus read failed, using last known data: %s", err)
            if self._last_known_data:
                return self._last_known_data
            raise UpdateFailed("Initial Modbus read failed with no backup: %s" % err)
