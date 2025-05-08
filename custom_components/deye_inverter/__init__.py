"""Initialization of the Deye Inverter integration."""

import logging

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SERIAL, CONF_INSTALLED_POWER

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration via YAML (import)."""
    conf = config.get(DOMAIN)
    if not conf:
        return True
    _LOGGER.debug("Importing YAML configuration: %s", conf)
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_HOST: conf[CONF_HOST],
                CONF_PORT: conf[CONF_PORT],
                CONF_SERIAL: conf[CONF_SERIAL],
                CONF_INSTALLED_POWER: conf[CONF_INSTALLED_POWER],
            },
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    from .coordinator import DeyeDataUpdateCoordinator

    installed_power = entry.data[CONF_INSTALLED_POWER]

    coordinator = DeyeDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        installed_power=installed_power,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the configuration to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and its platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
