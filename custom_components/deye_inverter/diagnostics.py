"""Diagnostics for the Deye Inverter integration.

Register maps differ between models in ways the protocol documentation does
not describe, so most reports come down to "what does this inverter actually
put in these registers". This dump answers that in one download: the raw
blocks as read, block by block, next to the values parsed from them.
"""

from __future__ import annotations

from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import (
    CONF_HOST,
    CONF_SERIAL,
    CORE_REGISTER_BLOCKS,
    DOMAIN,
    OPTIONAL_REGISTER_BLOCKS,
)

# The host and serial identify the installation, not the inverter model, so
# they are of no use in a bug report. Inverter ID is the device's own serial.
TO_REDACT = {CONF_HOST, CONF_SERIAL}
TO_REDACT_METRICS = {"Inverter ID"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> Dict[str, Any]:
    """Return the raw registers and parsed values for one inverter."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    inverter = getattr(coordinator, "inverter", None)

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "scaling_variant": getattr(coordinator, "mod", None),
        "register_blocks": {
            "core": [f"0x{s:04X}-0x{e:04X}" for s, e in CORE_REGISTER_BLOCKS],
            "optional": [f"0x{s:04X}-0x{e:04X}" for s, e in OPTIONAL_REGISTER_BLOCKS],
        },
        "last_read": {
            "register_count": len(getattr(inverter, "last_raw", []) or []),
            "blocks": getattr(inverter, "last_blocks", []) or [],
        },
        "parsed": async_redact_data(
            dict(getattr(coordinator, "data", None) or {}), TO_REDACT_METRICS
        ),
    }
