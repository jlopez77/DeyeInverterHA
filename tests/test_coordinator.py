import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.deye_inverter.coordinator import DeyeDataUpdateCoordinator


class MockConfigEntry:
    def __init__(self, domain, data, entry_id="test_entry"):
        self.domain = domain
        self.data = data
        self.entry_id = entry_id


@pytest.fixture
def mock_hass():
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_config_entry():
    return MockConfigEntry(
        domain="deye_inverter",
        data={
            "host": "192.168.1.100",
            "port": 502,
            "serial": "ABC123",
            "installed_power": 5000,
        }
    )


@pytest.fixture
def mock_inverter_data():
    mock = AsyncMock()
    mock.fetch_data.return_value = {
        0x00BA: 500,
        0x00BB: 300,
    }
    return mock


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_update_success(mock_inverter_class, mock_hass, mock_config_entry, mock_inverter_data):
    """Test successful data update."""
    mock_inverter_class.return_value = mock_inverter_data

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    data = await coordinator._async_update_data()
    assert data == {0x00BA: 500, 0x00BB: 300}
    mock_inverter_data.fetch_data.assert_awaited_once()


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_update_failure_no_cache(mock_inverter_class, mock_hass, mock_config_entry):
    """Test that UpdateFailed is raised if no cache is available on failure."""
    mock_inverter = AsyncMock()
    mock_inverter.fetch_data.side_effect = Exception("connection error")
    mock_inverter_class.return_value = mock_inverter

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_update_failure_with_cache(mock_inverter_class, mock_hass, mock_config_entry):
    """Test that last known data is returned on failure."""
    mock_inverter = AsyncMock()
    mock_inverter.fetch_data.side_effect = Exception("temporary failure")
    mock_inverter_class.return_value = mock_inverter

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    coordinator._last_known_data = {"PV1 Power": 500}

    result = await coordinator._async_update_data()
    assert result == {"PV1 Power": 500}
