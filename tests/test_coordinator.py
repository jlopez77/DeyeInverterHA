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
    hass = MagicMock(spec=HomeAssistant)
    # Run executor jobs inline so lazy inverter creation works in tests
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    return hass


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


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_unreachable_inverter_no_cache(
    mock_inverter_class, mock_hass, mock_config_entry
):
    """UpdateFailed is raised when the inverter cannot be created and no cache."""
    from pysolarmanv5.pysolarmanv5 import NoSocketAvailableError

    mock_inverter_class.side_effect = NoSocketAvailableError("No socket available")

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    assert coordinator.inverter is None
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_unreachable_inverter_with_cache(
    mock_inverter_class, mock_hass, mock_config_entry
):
    """Last known data is returned when the inverter cannot be created."""
    from pysolarmanv5.pysolarmanv5 import NoSocketAvailableError

    mock_inverter_class.side_effect = NoSocketAvailableError("No socket available")

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )
    coordinator._last_known_data = {"PV1 Power": 500}

    result = await coordinator._async_update_data()
    assert result == {"PV1 Power": 500}


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_configured_variant_reaches_the_inverter_client(
    mock_inverter_class, mock_hass, mock_config_entry
):
    """The variant stored in the entry is what the client parses with."""
    mock_config_entry.data = {**mock_config_entry.data, "mod": 2}

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )
    coordinator._create_inverter()

    assert coordinator.mod == 2
    assert coordinator.profile.mod == 2
    assert mock_inverter_class.call_args.kwargs["mod"] == 2


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_options_override_the_variant_from_data(
    mock_inverter_class, mock_hass, mock_config_entry
):
    """A variant changed through the options flow wins over setup data."""
    mock_config_entry.data = {**mock_config_entry.data, "mod": 2}
    mock_config_entry.options = {"mod": 0}

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    assert coordinator.mod == 0


@patch("custom_components.deye_inverter.coordinator.InverterData")
@pytest.mark.asyncio
async def test_unknown_variant_falls_back_to_default(
    mock_inverter_class, mock_hass, mock_config_entry
):
    """A junk variant in the entry must not break setup."""
    mock_config_entry.data = {**mock_config_entry.data, "mod": "nonsense"}

    coordinator = DeyeDataUpdateCoordinator(
        hass=mock_hass,
        config_entry=mock_config_entry,
        installed_power=5000,
    )

    assert coordinator.mod == 0
