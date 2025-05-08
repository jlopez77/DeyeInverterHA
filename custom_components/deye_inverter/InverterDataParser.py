import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple, Union

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
            _LOGGER.error("Could not read DYRealTime.txt: %s", e)
            return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        _LOGGER.error("Error parsing DYRealTime.txt: %s", e)
        return {}


_DEFINITIONS = _load_definitions()

_ENUM_MAPPINGS: Dict[Tuple[int, str], Dict[int, str]] = {}
_sections: Sequence[Dict[str, Any]] = (
    list(_DEFINITIONS.values())
    if isinstance(_DEFINITIONS, dict)
    else _DEFINITIONS  # type: ignore[assignment]
)

# Only build enums if valid optionRanges exist AND interactionType == 2
for section in _sections:
    for item in section.get("items", []):
        option_ranges = item.get("optionRanges")
        if (
            isinstance(option_ranges, list)
            and option_ranges
            and item.get("interactionType") == 2
        ):
            title = item.get("titleEN")
            if not title:
                continue

            mapping: Dict[int, str] = {}
            for opt in option_ranges:
                key = opt.get("key")
                val = opt.get("valueEN")
                if isinstance(key, int) and isinstance(val, str):
                    mapping[key] = val

            for reg_hex in item.get("registers", []):
                try:
                    reg = int(reg_hex, 16)
                    _ENUM_MAPPINGS[(reg, title)] = mapping
                except (ValueError, TypeError):
                    continue


def combine_registers(
    registers: List[int], signed: bool = True, reverse: bool = False
) -> int:
    if reverse and len(registers) == 2:
        registers = list(reversed(registers))
    value = 0
    for reg in registers:
        value = (value << 16) | (reg & 0xFFFF)
    if signed:
        bits = 16 * len(registers)
        if value & (1 << (bits - 1)):
            value -= 1 << bits
    return value


def parse_battery_status(value: int) -> str:
    if value > 0:
        return "Discharge"
    elif value < 0:
        return "Charge"
    else:
        return "Stand-by"


def parse_grid_status(value: int) -> str:
    if value > 0:
        return "BUY"
    elif value < 0:
        return "SELL"
    else:
        return "Stand-by"


def parse_smartload_status(value: int) -> str:
    if value == 1:
        return "ON"
    elif value == 0:
        return "OFF"
    else:
        return f"Unknown ({value})"


def parse_grid_connected_status(value: int) -> str:
    return "On-Grid" if value == 1 else "Off-Grid"


def parse_gen_connected_status(value: int) -> str:
    return "On" if value == 1 else "Off"


def parse_raw(raw: List[int]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    first_len = 0x0070 - 0x003B + 1

    REVERSED_FIELDS = {
        "Total Production",
        "Total Load Consumption",
        "Total Energy Sold",
        "Total Energy Bought",
        "Total Grid Production",
    }

    if isinstance(_DEFINITIONS, dict):
        sections: Sequence[Dict[str, Any]] = list(_DEFINITIONS.values())
    elif isinstance(_DEFINITIONS, list):
        sections = _DEFINITIONS  # type: ignore[assignment]
    else:
        _LOGGER.error("Invalid definitions type: %s", type(_DEFINITIONS))
        return result

    for section in sections:
        for item in section.get("items", []):
            title = item.get("titleEN")
            if not title:
                continue

            try:
                ratio = float(item.get("ratio", 1))
                offset = float(item.get("offset", 0))
                signed = bool(item.get("signed", True))
                parser_rule = item.get("parserRule")
                registers = item.get("registers", [])

                if not registers:
                    continue

                indices = []
                for reg_hex in registers:
                    reg = int(reg_hex, 16)
                    if 0x003B <= reg <= 0x0070:
                        idx = reg - 0x003B
                    elif 0x0096 <= reg <= 0x00C3:
                        idx = first_len + (reg - 0x0096)
                    elif 0x0003 <= reg <= 0x00F8:
                        idx = reg  # generic fallback indexing
                    else:
                        continue
                    indices.append(idx)

                block = [raw[i] for i in indices if 0 <= i < len(raw)]
                if not block:
                    continue

                # Rule 5: ASCII string
                if parser_rule == 5:
                    chars = []
                    for word in block:
                        chars.append((word >> 8) & 0xFF)
                        chars.append(word & 0xFF)
                    ascii_string = (
                        bytearray(chars)
                        .decode("ascii", errors="ignore")
                        .strip("\x00")
                        .strip()
                    )
                    if not ascii_string or any(ord(c) < 32 for c in ascii_string):
                        value = "0x" + "".join(f"{b:02X}" for b in chars)
                    else:
                        value = ascii_string
                    result[title] = value or None
                    continue

                reverse = title in REVERSED_FIELDS
                raw_int = combine_registers(block, signed=signed, reverse=reverse)

                # Custom logic overrides
                reg_key = int(registers[0], 16)
                if reg_key == 0x00BE and title == "Battery Status":
                    result[title] = f"{parse_battery_status(raw_int)} ({raw_int})"
                    continue
                if reg_key == 0x00A9 and title == "Grid Status":
                    result[title] = f"{parse_grid_status(raw_int)} ({raw_int})"
                    continue
                if reg_key == 0x00C3 and title == "SmartLoad Enable Status":
                    result[title] = f"{parse_smartload_status(raw_int)}"
                    continue
                if reg_key == 0x00C2 and title == "Grid-connected Status":
                    result[title] = f"{parse_grid_connected_status(raw_int)}"
                    continue
                if reg_key == 0x00A6 and title == "Gen-connected Status":
                    result[title] = f"{parse_gen_connected_status(raw_int)}"
                    continue

                # Enum mapping by (register, title)
                mapping = _ENUM_MAPPINGS.get((reg_key, title))
                if mapping and raw_int in mapping:
                    result[title] = f"{mapping[raw_int]} ({raw_int})"
                    continue
                elif mapping:
                    result[title] = f"Unknown ({raw_int})"
                    continue

                # Alert/bits
                if parser_rule == 6:
                    result[title] = raw_int
                    continue

                if title in ["Total Grid Production"]:
                    val = raw_int * ratio + offset
                    result[title] = f"{round(val, 2)} (raw: {raw_int})"
                else:
                    # Default: numeric
                    if "Temperature" in title:
                        val = raw_int * ratio - 100 + offset
                    else:
                        val = raw_int * ratio + offset
                    result[title] = float(round(val, 2))

            except Exception as e:
                _LOGGER.debug("Error parsing %s: %s", title, e)
                continue

    return result
