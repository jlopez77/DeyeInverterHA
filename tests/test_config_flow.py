from unittest.mock import patch

from custom_components.deye_inverter.const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    CONF_INSTALLED_POWER,
)

USER_INPUT = {
    CONF_HOST: "192.168.1.100",
    CONF_PORT: 8899,
    CONF_SERIAL: "123456789",
    CONF_INSTALLED_POWER: 5,
}


async def test_show_config_form(hass):
    """Test that the config form is displayed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_create_entry_from_user_input(hass):
    """A successful connection test creates the entry."""
    with patch(
        "custom_components.deye_inverter.config_flow.test_connection"
    ) as mock_test:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=USER_INPUT,
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "123456789"
    assert result["data"] == USER_INPUT
    mock_test.assert_called_once_with("192.168.1.100", 8899, "123456789")


async def test_cannot_connect_shows_error(hass):
    """A failing connection test re-shows the form with an error."""
    with patch(
        "custom_components.deye_inverter.config_flow.test_connection",
        side_effect=OSError("no route"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=USER_INPUT,
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_invalid_serial_shows_error(hass):
    """A non-numeric serial is rejected before any connection attempt."""
    with patch(
        "custom_components.deye_inverter.config_flow.test_connection"
    ) as mock_test:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**USER_INPUT, CONF_SERIAL: "17ABC"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {CONF_SERIAL: "invalid_serial"}
    mock_test.assert_not_called()


async def test_duplicate_serial_aborts(hass):
    """A second entry with the same serial aborts."""
    with patch("custom_components.deye_inverter.config_flow.test_connection"):
        first = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=USER_INPUT
        )
        assert first["type"] == "create_entry"

        second = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=USER_INPUT
        )

    assert second["type"] == "abort"
    assert second["reason"] == "already_configured"
