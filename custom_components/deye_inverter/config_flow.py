import logging

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SERIAL, CONF_INSTALLED_POWER
from .InverterData import test_connection

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=8899): int,
        vol.Required(CONF_SERIAL): str,
        vol.Required(CONF_INSTALLED_POWER): int,
    }
)


class DeyeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Deye Inverter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries by serial number
            await self.async_set_unique_id(user_input[CONF_SERIAL])
            self._abort_if_unique_id_configured()

            if not user_input[CONF_SERIAL].strip().isdigit():
                errors[CONF_SERIAL] = "invalid_serial"
            else:
                try:
                    await self.hass.async_add_executor_job(
                        test_connection,
                        user_input[CONF_HOST],
                        user_input[CONF_PORT],
                        user_input[CONF_SERIAL],
                    )
                except Exception as err:
                    _LOGGER.warning("Cannot connect to inverter: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_SERIAL],
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    # YAML import (async_setup) funnels through the same validation
    async_step_import = async_step_user
