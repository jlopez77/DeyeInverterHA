import pytest

from custom_components.deye_inverter.const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    CONF_INSTALLED_POWER,
)


async def test_show_config_form(hass):
    """Test that the config form is displayed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_create_entry_from_user_input(hass):
    """Test creating a config entry from user input."""
    user_input = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8899,
        CONF_SERIAL: "123456789",
        CONF_INSTALLED_POWER: 5000,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data=user_input,
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "123456789"
    assert result["data"] == user_input

