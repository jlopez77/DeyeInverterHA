"""Per-model scaling variants of the register definitions.

The same register map serves the whole single-phase hybrid family, but not
every generation reports the same units: the higher-power models report load,
grid and CT power in units of 10 W, and some of them battery current in 0.1 A.
The protocol documentation only covers the smaller inverters, so the variant
cannot be derived from it — the user selects it (``mod``), exactly as the
community Solarman profiles for this family do, and the ratio lists in
DYRealTime.txt are indexed by it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Tuple, Union

from .const import DEFAULT_MOD, MOD_VARIANTS
from .InverterDataParser import (
    _build_enum_mappings,
    _DEFINITIONS,
    _ENUM_MAPPINGS,
    _RAW_DEFINITIONS,
    resolve_variant,
)

Definitions = Union[Dict[str, Any], List[Any]]


@dataclass(frozen=True, eq=False)
class Profile:
    """Register definitions resolved for one scaling variant."""

    mod: int
    definitions: Definitions
    enum_mappings: Dict[Tuple[int, str], Dict[int, str]]


def normalize_mod(value: Any) -> int:
    """Coerce a configured variant to a known one, falling back to default."""
    try:
        mod = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MOD
    return mod if mod in MOD_VARIANTS else DEFAULT_MOD


@lru_cache(maxsize=len(MOD_VARIANTS))
def get_profile(mod: int = DEFAULT_MOD) -> Profile:
    """Return the profile for a scaling variant, resolved once and cached."""
    mod = normalize_mod(mod)
    if mod == DEFAULT_MOD:
        # Reuse the module-level definitions the default path already parses
        return Profile(DEFAULT_MOD, _DEFINITIONS, _ENUM_MAPPINGS)
    definitions = resolve_variant(_RAW_DEFINITIONS, mod)
    return Profile(mod, definitions, _build_enum_mappings(definitions))
