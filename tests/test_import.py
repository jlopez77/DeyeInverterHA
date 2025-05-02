import os
import sys
import types

# 1) Asegura que pytest vea tu integración
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2) Define stubs para los módulos y clases de Home Assistant que se importan
stubs = {
    # Módulos vacíos o con clases stub
    "homeassistant": {},
    "homeassistant.core": {
        "HomeAssistant": type("HomeAssistant", (), {}),
    },
    "homeassistant.config_entries": {
        "ConfigEntry": type("ConfigEntry", (), {}),
    },
    "homeassistant.helpers": {},
    "homeassistant.helpers.update_coordinator": {
        "CoordinatorEntity": type("CoordinatorEntity", (), {}),
    },
    "homeassistant.helpers.entity": {
        "EntityCategory": type("EntityCategory", (), {}),
    },
    "homeassistant.components.sensor": {
        "SensorEntity": type("SensorEntity", (), {}),
        "SensorDeviceClass": type("SensorDeviceClass", (), {}),
        "SensorStateClass": type("SensorStateClass", (), {}),
    },
}

for module_name, attrs in stubs.items():
    mod = types.ModuleType(module_name)
    for name, obj in attrs.items():
        setattr(mod, name, obj)
    sys.modules[module_name] = mod


def test_import_deye_inverter():
    """Comprueba que la integración se puede importar sin errores."""
    import custom_components.deye_inverter  # noqa: F401
