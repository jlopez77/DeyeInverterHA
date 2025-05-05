import json
import logging
from pathlib import Path
import importlib.resources as pkg_resources

# from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _load_definitions() -> dict | list:
    try:
        data = pkg_resources.read_text(__package__, "DYRealTime.txt")
    except Exception:
        fp = Path(__file__).parent / "DYRealTime.txt"
        try:
            data = fp.read_text()
        except Exception as e:
            _LOGGER.error("No se pudo leer DYRealTime.txt: %s", e)
            return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        _LOGGER.error("Error parsing DYRealTime.txt: %s", e)
        return {}


_DEFINITIONS = _load_definitions()


def combine_registers(registers: list[int], signed: bool = True) -> int:
    value = 0
    for reg in registers:
        value = (value << 16) | (reg & 0xFFFF)
    if signed:
        bits = 16 * len(registers)
        if value & (1 << (bits - 1)):
            value -= 1 << bits
    return value


def parse_raw(raw: list[int]) -> dict[int, float]:
    result: dict[int, float] = {}
    first_block_len = 0x0070 - 0x003B + 1

    # Determinar cómo iterar secciones
    if isinstance(_DEFINITIONS, dict):
        sections = list(_DEFINITIONS.values())
    elif isinstance(_DEFINITIONS, list):
        sections = _DEFINITIONS
    else:
        _LOGGER.error("Definiciones inválidas: %s", type(_DEFINITIONS))
        return result

    for section in sections:
        items = section.get("items", [])
        for item in items:
            title = item.get("titleEN", "")
            ratio = float(item.get("ratio", 1))
            offset = float(item.get("offset", 0))
            signed = item.get("signed", True)
            length = item.get("length", 1)

            # Iterar cada registro declarado
            for reg_hex in item.get("registers", []):
                try:
                    reg = int(reg_hex, 16)
                except ValueError:
                    continue

                # Calcular índice en raw
                if 0x003B <= reg <= 0x0070:
                    idx = reg - 0x003B
                elif 0x0096 <= reg <= 0x00C3:
                    idx = first_block_len + (reg - 0x0096)
                else:
                    continue

                regs = raw[idx: idx + length]
                raw_int = combine_registers(regs, signed)

                # Ajuste de temperatura
                if "Temperature" in title:
                    val = raw_int * ratio - 100 + offset
                else:
                    val = raw_int * ratio + offset

                result[reg] = round(val, 2)

    return result
