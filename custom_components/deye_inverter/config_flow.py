import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    CONF_INSTALLED_POWER,
    CONF_MOD,
    DEFAULT_MOD,
    MOD_VARIANTS,
)
from .InverterData import test_connection
from .profiles import normalize_mod

_LOGGER = logging.getLogger(__name__)

MOD_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[str(mod) for mod in MOD_VARIANTS],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key=CONF_MOD,
    )
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=8899): int,
        vol.Required(CONF_SERIAL): str,
        vol.Required(CONF_INSTALLED_POWER): int,
        vol.Optional(CONF_MOD, default=str(DEFAULT_MOD)): MOD_SELECTOR,
    }
)


class DeyeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Deye Inverter."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "DeyeOptionsFlow":
        """Return the options flow, which can change the scaling variant."""
        return DeyeOptionsFlow()

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
                    # The selector hands back strings; store the variant as int
                    data = dict(user_input)
                    data[CONF_MOD] = normalize_mod(data.get(CONF_MOD, DEFAULT_MOD))
                    return self.async_create_entry(
                        title=user_input[CONF_SERIAL],
                        data=data,
                    )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    # YAML import (async_setup) funnels through the same validation
    async_step_import = async_step_user


class DeyeOptionsFlow(config_entries.OptionsFlow):
    """Change the scaling variant of an existing inverter."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_MOD: normalize_mod(user_input.get(CONF_MOD, DEFAULT_MOD))}
            )

        entry = self.config_entry
        current = normalize_mod(
            entry.options.get(CONF_MOD, entry.data.get(CONF_MOD, DEFAULT_MOD))
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_MOD, default=str(current)): MOD_SELECTOR}
            ),
        )
