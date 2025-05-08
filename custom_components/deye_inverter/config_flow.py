import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SERIAL, CONF_INSTALLED_POWER

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
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        # Prevent duplicate entries by serial number
        await self.async_set_unique_id(user_input[CONF_SERIAL])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=user_input[CONF_SERIAL],
            data=user_input,
        )
