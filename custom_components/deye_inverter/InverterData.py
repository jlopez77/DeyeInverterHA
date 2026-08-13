import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pysolarmanv5.pysolarmanv5 import PySolarmanV5, NoSocketAvailableError

from .const import (
    CORE_REGISTER_BLOCKS,
    DEFAULT_MOD,
    DEFAULT_MODBUS_TIMEOUT,
    OPTIONAL_REGISTER_BLOCKS,
)
from .InverterDataParser import parse_raw
from .profiles import get_profile

_LOGGER = logging.getLogger(__name__)


class ModbusReadError(Exception):
    """Raised when reading registers from the inverter fails."""


def _block_report(
    start: int, end: int, regs: Optional[List[int]], error: Optional[str] = None
) -> Dict[str, Any]:
    """Describe one block read, for the diagnostics download."""
    report: Dict[str, Any] = {
        "range": f"0x{start:04X}-0x{end:04X}",
        "expected": end - start + 1,
        "received": len(regs) if regs is not None else 0,
        "ok": regs is not None,
    }
    if error is not None:
        report["error"] = error
    if regs is not None:
        report["registers"] = {f"0x{start + i:04X}": v for i, v in enumerate(regs)}
        report["hex"] = " ".join(f"{v:04X}" for v in regs)
    return report


@dataclass(frozen=True)
class DeviceCapabilities:
    """What the inverter reports about itself, when it reports it."""

    rated_power: Optional[float] = None  # W
    mppts: Optional[int] = None
    phases: Optional[int] = None


def test_connection(host: str, port: int, serial: str) -> DeviceCapabilities:
    """Open a connection, read one register and the device capabilities.

    Raises on a failed connection; the capability read is best-effort, since
    not every device exposes those registers. Blocking: must run in an
    executor.
    """
    modbus = PySolarmanV5(
        host,
        int(serial),
        port=port,
        mb_slave_id=1,
        timeout=DEFAULT_MODBUS_TIMEOUT,
        verbose=False,
        auto_reconnect=False,
        logger=_LOGGER,
    )
    try:
        modbus.read_holding_registers(
            register_addr=CORE_REGISTER_BLOCKS[0][0], quantity=1
        )
        return _read_capabilities(modbus)
    finally:
        try:
            modbus.disconnect()
        except Exception:  # pragma: no cover - best-effort cleanup
            pass


def _read_capabilities(modbus: PySolarmanV5) -> DeviceCapabilities:
    """Read rated power (0x0010-0x0011) and the counts packed in 0x0012."""
    try:
        regs = modbus.read_holding_registers(register_addr=0x0010, quantity=3)
        low, high, counts = regs[0], regs[1], regs[2]
        # 32-bit value, low word first, in 0.1 W steps
        rated_power = (((high << 16) | low) & 0xFFFFFFFF) * 0.1
        # The counts are only meaningful once the register is populated
        mppts = (counts & 0x0F00) >> 8 if counts >= 0x0101 else None
        phases = counts & 0x000F if counts >= 0x0101 else None
        _LOGGER.debug(
            "Device capabilities: %s W, %s MPPTs, %s phases",
            rated_power,
            mppts,
            phases,
        )
        return DeviceCapabilities(
            rated_power=rated_power or None, mppts=mppts, phases=phases
        )
    except Exception as e:
        _LOGGER.debug("Device capability registers unavailable: %s", e)
        return DeviceCapabilities()


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
        mod: int = DEFAULT_MOD,
    ):
        self._host = host
        self._port = port
        self._serial = int(serial)
        self._hass = hass
        self._config_entry = config_entry
        self._profile = get_profile(mod)
        self._error_count = 0
        self._max_errors = 5
        # Kept for the diagnostics download: the last registers read, and how
        # each block fared
        self.last_raw: List[Optional[int]] = []
        self.last_blocks: List[Dict[str, Any]] = []

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
            regs = self._modbus.read_holding_registers(
                register_addr=addr, quantity=length
            )
            # A short answer would shift every later register in the flat
            # list, quietly turning one metric's value into another's
            if len(regs) != length:
                raise ModbusReadError(
                    f"Block 0x{addr:04X}: asked for {length} registers, "
                    f"got {len(regs)}"
                )
            return regs

        raw: List[Optional[int]] = []
        blocks: List[Dict[str, Any]] = []

        try:
            for start, end in CORE_REGISTER_BLOCKS:
                length = end - start + 1
                regs = await loop.run_in_executor(None, read_block, start, length)
                _LOGGER.debug("Regs block 0x%04X (%d): %s", start, length, regs)
                raw.extend(regs)
                blocks.append(_block_report(start, end, regs))
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
                blocks.append(_block_report(start, end, regs))
            except Exception as e:
                _LOGGER.debug(
                    "Optional register block 0x%04X unavailable: %s", start, e
                )
                raw.extend([None] * length)
                blocks.append(_block_report(start, end, None, error=str(e)))
            await asyncio.sleep(0.1)

        _LOGGER.debug("RAW registers (total %d): %s", len(raw), raw)

        self.last_raw = raw
        self.last_blocks = blocks

        return parse_raw(raw, self._profile)

    async def _trigger_reload(self):
        if not self._hass or not self._config_entry:
            _LOGGER.error("Cannot reload: 'hass' or 'config_entry' is missing.")
            return
        # Fire and forget: awaiting the reload here would deadlock, since it
        # tears down the coordinator this fetch is running under.
        self._hass.async_create_task(
            self._hass.config_entries.async_reload(self._config_entry.entry_id)
        )
