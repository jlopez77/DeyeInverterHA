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
    Envía peticiones Modbus RTU sobre TCP al inversor usando PySolarmanV5,
    que internamente gestiona framing, unit id y checksum.
    """

    def __init__(self, host: str, port: int = 8899, serial: str = "1"):
        """
        host: dirección IP del inversor
        port: puerto Modbus/TCP
        serial: número de serie del inversor
        """
        self._host = host
        self._port = port
        self._serial = int(serial)
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

    async def fetch_data(self) -> Dict[int, Any]:
        """Lee dos bloques de registros y retorna el dict parseado."""
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
            regs1 = await loop.run_in_executor(
                None, read_block, first_addr, first_len
            )
            # Pausa para evitar desajuste de secuencia interno
            await asyncio.sleep(0.1)
            regs2 = await loop.run_in_executor(
                None, read_block, second_addr, second_len
            )
        except Exception as e:
            _LOGGER.error("Error leyendo registros: %s", e)
            raise ModbusException(e)

        _LOGGER.debug("Regs bloque1 (%s, %s): %s", first_addr, first_len, regs1)
        _LOGGER.debug("Regs bloque2 (%s, %s): %s", second_addr, second_len, regs2)

        raw = regs1 + regs2
        _LOGGER.debug("RAW registers (total %d): %s", len(raw), raw)

        return parse_raw(raw)
