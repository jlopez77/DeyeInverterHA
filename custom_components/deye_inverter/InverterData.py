import asyncio
import logging
from typing import Any, Dict

from pymodbus.exceptions import ModbusException
from pysolarmanv5.pysolarmanv5 import PySolarmanV5

from .const import DEFAULT_MODBUS_TIMEOUT
from .InverterDataParser import parse_raw

_LOGGER = logging.getLogger(__name__)


class InverterData:
    """
    Sends Modbus RTU over TCP requests to the inverter using PySolarmanV5,
    which handles framing, unit id, and checksum internally.
    """

    def __init__(self, host: str, port: int = 8899, serial: str = "1", hass=None, config_entry=None):
        self._host = host
        self._port = port
        self._serial = int(serial)
        self._hass = hass
        self._config_entry = config_entry
        self._error_count = 0
        self._max_errors = 5

        self._modbus = PySolarmanV5(
            self._host,
            self._serial,
            port=self._port,
            mb_slave_id=1,
            timeout=DEFAULT_MODBUS_TIMEOUT,
            verbose=False,
            auto_reconnect=True,
            logger=_LOGGER,
        )

    async def fetch_data(self) -> Dict[str, Any]:
        """Reads two register blocks and returns the parsed dictionary."""
        loop = asyncio.get_running_loop()
        first_addr = 0x003B
        first_len = 0x0070 - first_addr + 1
        second_addr = 0x0096
        second_len = 0x00C3 - second_addr + 1

        def read_block(addr: int, length: int) -> list[int]:
            return self._modbus.read_holding_registers(
                register_addr=addr, quantity=length
            )

        try:
            regs1 = await loop.run_in_executor(None, read_block, first_addr, first_len)
            await asyncio.sleep(0.1)
            regs2 = await loop.run_in_executor(None, read_block, second_addr, second_len)
            self._error_count = 0  # Reset on success
        except Exception as e:
            _LOGGER.error("Error reading registers: %s", e)
            self._error_count += 1
            if self._error_count >= self._max_errors:
                _LOGGER.error("Max consecutive read errors reached (%d). Reloading integration.", self._max_errors)
                await self._trigger_reload()
            raise ModbusException(e)

        _LOGGER.debug("Regs block1 (%s, %s): %s", first_addr, first_len, regs1)
        _LOGGER.debug("Regs block2 (%s, %s): %s", second_addr, second_len, regs2)

        raw = regs1 + regs2
        _LOGGER.debug("RAW registers (total %d): %s", len(raw), raw)

        return parse_raw(raw)

    async def _trigger_reload(self):
        if not self._hass or not self._config_entry:
            _LOGGER.error("Cannot reload integration: 'hass' or 'config_entry' is missing.")
            return
        await self._hass.services.async_call(
            "homeassistant",
            "reload_config_entry",
            {"entry_id": self._config_entry.entry_id},
            blocking=False,
        )
