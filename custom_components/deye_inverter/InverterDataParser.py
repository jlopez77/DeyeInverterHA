import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

import importlib.resources as pkg_resources

from .const import DEFAULT_MOD, REGISTER_BLOCKS

if TYPE_CHECKING:  # pragma: no cover - import cycle only exists for typing
    from .profiles import Profile

_LOGGER = logging.getLogger(__name__)

# Definition keys whose value may be a per-variant list instead of a scalar
_VARIANT_KEYS = ("ratio", "offset")


def _load_definitions() -> Union[Dict[str, Any], List[Any]]:
    try:
        data = (pkg_resources.files(__package__) / "DYRealTime.txt").read_text()
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


def iter_sections(
    definitions: Union[Dict[str, Any], List[Any], Any],
) -> Sequence[Dict[str, Any]]:
    """Return the sections of a definitions document, whatever shape it has."""
    if isinstance(definitions, dict):
        return list(definitions.values())
    if isinstance(definitions, list):
        return definitions
    _LOGGER.error("Invalid definitions type: %s", type(definitions))
    return []


def select_variant(value: Any, mod: int) -> Any:
    """Pick the entry a scaling variant uses from a per-variant list.

    Scalars are returned unchanged, so only the items that actually differ
    between inverter generations need a list. A variant beyond the end of the
    list reuses the last entry, matching the community profiles this borrows
    the convention from.
    """
    if not isinstance(value, list) or not value:
        return value
    return value[mod] if 0 <= mod < len(value) else value[-1]


def resolve_variant(
    definitions: Union[Dict[str, Any], List[Any]], mod: int
) -> Union[Dict[str, Any], List[Any]]:
    """Collapse the per-variant lists in the definitions down to scalars.

    Done once per variant at load time, so the polling path keeps reading
    plain numbers and stays unaware that variants exist.
    """
    resolved = deepcopy(definitions)
    for section in iter_sections(resolved):
        if not isinstance(section, dict):
            continue
        for item in section.get("items", []):
            for key in _VARIANT_KEYS:
                if key in item:
                    item[key] = select_variant(item[key], mod)
    return resolved


def register_index(reg: int) -> Optional[int]:
    """Map a register address to its index in the flat register list."""
    offset = 0
    for start, end in REGISTER_BLOCKS:
        if start <= reg <= end:
            return offset + (reg - start)
        offset += end - start + 1
    return None


# Definitions exactly as shipped, per-variant lists included
_RAW_DEFINITIONS = _load_definitions()
# ...and resolved for the default variant, which every module-level consumer
# (and every caller that passes no profile) uses.
_DEFINITIONS = resolve_variant(_RAW_DEFINITIONS, DEFAULT_MOD)


def _build_enum_mappings(
    definitions: Union[Dict[str, Any], List[Any]],
) -> Dict[Tuple[int, str], Dict[int, str]]:
    """Build (register, title) -> {key: label} from optionRanges."""
    mappings: Dict[Tuple[int, str], Dict[int, str]] = {}

    # Only build enums if valid optionRanges exist AND interactionType == 2
    for section in iter_sections(definitions):
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
                    # Some items label their options "value" instead of
                    # "valueEN" (e.g. Work Mode, Time of use)
                    val = opt.get("valueEN") or opt.get("value")
                    if isinstance(key, int) and isinstance(val, str):
                        mapping[key] = val

                for reg_hex in item.get("registers", []):
                    try:
                        reg = int(reg_hex, 16)
                        mappings[(reg, title)] = mapping
                    except (ValueError, TypeError):
                        continue
    return mappings


_ENUM_MAPPINGS = _build_enum_mappings(_DEFINITIONS)


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


def parse_raw(
    raw: Sequence[Optional[int]], profile: Optional["Profile"] = None
) -> Dict[str, Any]:
    """Parse a flat register list into {metric title: value}.

    Without a profile the default scaling variant is used, so existing
    callers and tests keep the documented behaviour.
    """
    result: Dict[str, Any] = {}

    REVERSED_FIELDS = {
        "Total Production",
        "Total Load Consumption",
        "Total Energy Sold",
        "Total Energy Bought",
        "Total Grid Production",
        "Total Battery Charge",
        "Total Battery Discharge",
    }

    definitions = _DEFINITIONS if profile is None else profile.definitions
    enum_mappings = _ENUM_MAPPINGS if profile is None else profile.enum_mappings

    for section in iter_sections(definitions):
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
                    idx = register_index(int(reg_hex, 16))
                    if idx is not None:
                        indices.append(idx)

                values = [raw[i] for i in indices if 0 <= i < len(raw)]
                # None marks an optional block that could not be read
                block = [v for v in values if v is not None]
                if not block or len(block) != len(values):
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
                if reg_key == 0x00F4 and title == "Work Mode" and len(block) == 2:
                    # 0x00F4 = mode (0 selling first, 1 zero-export to load,
                    # 2 zero-export to home), 0x00F7 = solar sell flag. The
                    # optionRanges keys encode the pair: with solar sell the
                    # mode keeps its key, without it the key is shifted by 2.
                    mode, solar_sell = block
                    key = 0 if mode == 0 else (mode if solar_sell else mode + 2)
                    wm_mapping = enum_mappings.get((reg_key, title), {})
                    result[title] = wm_mapping.get(
                        key, f"Unknown ({mode}/{solar_sell})"
                    )
                    continue
                if reg_key == 0x00BE and title == "Battery Status":
                    result[title] = parse_battery_status(raw_int)
                    continue
                if reg_key == 0x00A9 and title == "Grid Status":
                    result[title] = parse_grid_status(raw_int)
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
                mapping = enum_mappings.get((reg_key, title))
                if mapping and raw_int in mapping:
                    result[title] = mapping[raw_int]
                    continue
                elif mapping:
                    result[title] = f"Unknown ({raw_int})"
                    continue

                # Alert/bitfields: store as hex string to stay JSON-serializable
                if parser_rule == 6:
                    result[title] = "0x" + "".join(f"{w:04X}" for w in block)
                    continue

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
