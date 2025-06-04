import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pysolarmanv5.pysolarmanv5 import NoSocketAvailableError

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
        assert config_entry is not None  # ✅ for mypy

        self.hass = hass
        self.config_entry = config_entry
        self.installed_power = installed_power
        self.serial = config_entry.data["serial"]
        self._last_known_data: Dict[str, Any] = {}
        self.inverter = None

        try:
            self.inverter = InverterData(
                host=config_entry.data["host"],
                port=config_entry.data.get("port", 8899),
                serial=config_entry.data["serial"],
                hass=hass,
                config_entry=config_entry,
            )
        except NoSocketAvailableError as e:
            _LOGGER.warning("Inverter not reachable during setup: %s", e)

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
        if self.inverter is None:
            if self.config_entry is None:
                raise UpdateFailed("No config entry available to create inverter.")
            try:
                self.inverter = InverterData(
                    host=self.config_entry.data["host"],
                    port=self.config_entry.data.get("port", 8899),
                    serial=self.config_entry.data["serial"],
                    hass=self.hass,
                    config_entry=self.config_entry,
                )
            except NoSocketAvailableError as e:
                _LOGGER.warning("Inverter still unreachable: %s", e)
                if self._last_known_data:
                    return self._last_known_data
                raise UpdateFailed(f"Inverter still unreachable: {e}")

        try:
            data = await self.inverter.fetch_data()
            self._last_known_data = data
            return data
        except Exception as err:
            _LOGGER.warning("Modbus read failed, using last known data: %s", err)
            if self._last_known_data:
                return self._last_known_data
            raise UpdateFailed("Initial Modbus read failed with no backup: %s" % err)
