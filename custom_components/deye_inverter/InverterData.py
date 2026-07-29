import asyncio
import logging
from typing import Any, Dict, List, Optional

from pysolarmanv5.pysolarmanv5 import PySolarmanV5, NoSocketAvailableError

from .const import (
    CORE_REGISTER_BLOCKS,
    DEFAULT_MODBUS_TIMEOUT,
    OPTIONAL_REGISTER_BLOCKS,
)
from .InverterDataParser import parse_raw

_LOGGER = logging.getLogger(__name__)


class ModbusReadError(Exception):
    """Raised when reading registers from the inverter fails."""


class InverterData:
    """
    Sends Modbus RTU over TCP requests to the inverter using PySolarmanV5,
    which handles framing, unit id, and checksum internally.
    """

    def __init__(
        self,
        host: str,
        port: int = 8899,
        serial: str = "1",
        hass=None,
        config_entry=None,
    ):
        self._host = host
        self._port = port
        self._serial = int(serial)
        self._hass = hass
        self._config_entry = config_entry
        self._error_count = 0
        self._max_errors = 5

        try:
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
        except NoSocketAvailableError as e:
            _LOGGER.warning("No socket available when connecting to inverter: %s", e)
            raise

    async def fetch_data(self) -> Dict[str, Any]:
        """Reads the register blocks and returns the parsed dictionary."""
        loop = asyncio.get_running_loop()

        def read_block(addr: int, length: int) -> list[int]:
            return self._modbus.read_holding_registers(
                register_addr=addr, quantity=length
            )

        raw: List[Optional[int]] = []

        try:
            for start, end in CORE_REGISTER_BLOCKS:
                length = end - start + 1
                regs = await loop.run_in_executor(None, read_block, start, length)
                _LOGGER.debug("Regs block 0x%04X (%d): %s", start, length, regs)
                raw.extend(regs)
                await asyncio.sleep(0.1)
            self._error_count = 0  # Reset on success
        except Exception as e:
            _LOGGER.error("Error reading registers: %s", e)
            self._error_count += 1
            if self._error_count >= self._max_errors:
                _LOGGER.error(
                    "Max consecutive read errors reached (%d). Reloading integration.",
                    self._max_errors,
                )
                await self._trigger_reload()
            raise ModbusReadError(str(e)) from e

        # Optional blocks (device info, work mode): some devices do not
        # expose them, so a failure only skips their metrics for this cycle.
        for start, end in OPTIONAL_REGISTER_BLOCKS:
            length = end - start + 1
            try:
                regs = await loop.run_in_executor(None, read_block, start, length)
                _LOGGER.debug("Regs block 0x%04X (%d): %s", start, length, regs)
                raw.extend(regs)
            except Exception as e:
                _LOGGER.debug(
                    "Optional register block 0x%04X unavailable: %s", start, e
                )
                raw.extend([None] * length)
            await asyncio.sleep(0.1)

        _LOGGER.debug("RAW registers (total %d): %s", len(raw), raw)

        return parse_raw(raw)

    async def _trigger_reload(self):
        if not self._hass or not self._config_entry:
            _LOGGER.error("Cannot reload: 'hass' or 'config_entry' is missing.")
            return
        # Fire and forget: awaiting the reload here would deadlock, since it
        # tears down the coordinator this fetch is running under.
        self._hass.async_create_task(
            self._hass.config_entries.async_reload(self._config_entry.entry_id)
        )
