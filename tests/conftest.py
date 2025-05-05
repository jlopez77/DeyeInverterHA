import sys
from pathlib import Path

# Add the root of the project to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import the plugin's fixtures
pytest_plugins = ["pytest_homeassistant_custom_component"]

import pytest

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom_components during tests."""
    # This fixture is required for config flow and other integration-level logic
    pass
