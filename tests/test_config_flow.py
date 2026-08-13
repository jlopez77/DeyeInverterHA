from unittest.mock import patch

from custom_components.deye_inverter.const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    CONF_INSTALLED_POWER,
    CONF_MOD,
    DEFAULT_MOD,
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
    # The scaling variant defaults to the documented one and is stored as int
    assert result["data"] == {**USER_INPUT, CONF_MOD: DEFAULT_MOD}
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


async def test_selected_variant_is_stored_as_int(hass):
    """The selector hands back a string; the entry keeps an int."""
    with patch("custom_components.deye_inverter.config_flow.test_connection"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**USER_INPUT, CONF_MOD: "2"},
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_MOD] == 2


async def test_variant_is_detected_from_rated_power(hass):
    """A 10 kW inverter gets variant 2 without the user choosing it."""
    from custom_components.deye_inverter.InverterData import DeviceCapabilities

    with patch(
        "custom_components.deye_inverter.config_flow.test_connection",
        return_value=DeviceCapabilities(rated_power=10000.0, mppts=3, phases=1),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**USER_INPUT, CONF_MOD: "auto"},
        )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_MOD] == 2


async def test_detection_never_moves_a_small_inverter(hass):
    """Below the threshold, detection keeps the documented scaling."""
    from custom_components.deye_inverter.InverterData import DeviceCapabilities

    with patch(
        "custom_components.deye_inverter.config_flow.test_connection",
        return_value=DeviceCapabilities(rated_power=5000.0, mppts=2, phases=1),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**USER_INPUT, CONF_MOD: "auto"},
        )

    assert result["data"][CONF_MOD] == DEFAULT_MOD


async def test_options_flow_offers_only_concrete_variants(hass):
    """Detection happens at setup, so the options flow has no auto choice."""
    with patch("custom_components.deye_inverter.config_flow.test_connection"):
        created = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=USER_INPUT
        )
    entry = hass.config_entries.async_get_entry(created["result"].entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    options = result["data_schema"].schema[CONF_MOD].config["options"]

    assert options == ["0", "1", "2"]


async def test_options_flow_changes_the_variant(hass):
    """The variant can be changed after setup, without re-adding the entry."""
    with patch("custom_components.deye_inverter.config_flow.test_connection"):
        created = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=USER_INPUT
        )
    entry = hass.config_entries.async_get_entry(created["result"].entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_MOD: "2"}
    )

    assert result["type"] == "create_entry"
    assert entry.options[CONF_MOD] == 2
    # The connection details stay untouched
    assert entry.data[CONF_HOST] == USER_INPUT[CONF_HOST]


async def test_options_flow_defaults_to_the_configured_variant(hass):
    """The form opens on the variant currently in use."""
    with patch("custom_components.deye_inverter.config_flow.test_connection"):
        created = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**USER_INPUT, CONF_MOD: "2"},
        )
    entry = hass.config_entries.async_get_entry(created["result"].entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["data_schema"]({})[CONF_MOD] == "2"


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
