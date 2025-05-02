import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.deye_inverter.config_flow import DeyeConfigFlow
from custom_components.deye_inverter.const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SERIAL, CONF_INSTALLED_POWER

@pytest.fixture(autouse=True)
def bypass_setup(monkeypatch):
    monkeypatch.setattr(DeyeConfigFlow, "async_setup_entry", lambda *args, **kwargs: True)

async def test_config_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    user_input = {
        CONF_HOST: "192.0.2.1",
        CONF_PORT: 502,
        CONF_SERIAL: "ABCD1234",
        CONF_INSTALLED_POWER: 3000,
    }
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result2["type"] == "create_entry"
    assert result2["data"] == user_input

