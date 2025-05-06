import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

import importlib.resources as pkg_resources

_LOGGER = logging.getLogger(__name__)


def _load_definitions() -> Union[Dict[str, Any], List[Any]]:
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

# Construir mapeos de enums solo para parserRule == 2
_ENUM_MAPPINGS: Dict[int, Dict[int, str]] = {}
_sections: Sequence[Dict[str, Any]] = (
    list(_DEFINITIONS.values())
    if isinstance(_DEFINITIONS, dict)
    else _DEFINITIONS  # type: ignore[assignment]
)

for section in _sections:
    for item in section.get("items", []):
        if item.get("parserRule") != 2:
            continue
        opt_ranges = item.get("optionRanges")
        if not isinstance(opt_ranges, list):
            continue
        mapping: Dict[int, str] = {}
        for opt in opt_ranges:
            key = opt.get("key")
            val = opt.get("valueEN")
            if isinstance(key, int) and isinstance(val, str):
                mapping[key] = val
        for reg_hex in item.get("registers", []):
            try:
                reg = int(reg_hex, 16)
            except (ValueError, TypeError):
                continue
            _ENUM_MAPPINGS[reg] = mapping


def combine_registers(registers: List[int], signed: bool = True) -> int:
    value = 0
    for reg in registers:
        value = (value << 16) | (reg & 0xFFFF)
    if signed:
        bits = 16 * len(registers)
        if value & (1 << (bits - 1)):
            value -= 1 << bits
    return value


def parse_raw(raw: List[int]) -> Dict[int, Any]:
    result: Dict[int, Any] = {}
    first_len = 0x0070 - 0x003B + 1

    if isinstance(_DEFINITIONS, dict):
        sections: Sequence[Dict[str, Any]] = list(_DEFINITIONS.values())
    elif isinstance(_DEFINITIONS, list):
        sections = _DEFINITIONS  # type: ignore[assignment]
    else:
        _LOGGER.error("Definiciones inválidas: %s", type(_DEFINITIONS))
        return result

    for section in sections:
        for item in section.get("items", []):
            title = item.get("titleEN") or item.get("titleZH") or ""
            ratio = float(item.get("ratio", 1))
            offset = float(item.get("offset", 0))
            signed = bool(item.get("signed", True))
            length = int(item.get("length", 1))

            for reg_hex in item.get("registers", []):
                try:
                    reg = int(reg_hex, 16)
                except (ValueError, TypeError):
                    continue

                if 0x003B <= reg <= 0x0070:
                    idx = reg - 0x003B
                elif 0x0096 <= reg <= 0x00C3:
                    idx = first_len + (reg - 0x0096)
                else:
                    continue

                block = raw[idx : idx + length]
                raw_int = combine_registers(block, signed)

                # Aplicar enum mapping si corresponde
                mapping = _ENUM_MAPPINGS.get(reg)
                if mapping and raw_int in mapping:
                    result[reg] = mapping[raw_int]
                    continue

                # Cálculo numérico
                if "Temperature" in title:
                    val = raw_int * ratio - 100 + offset
                else:
                    val = raw_int * ratio + offset

                result[reg] = round(val, 2)

    return result
