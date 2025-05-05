"""Constantes de la integración Deye Inverter."""

DOMAIN = "deye_inverter"
DEFAULT_SCAN_INTERVAL = 30  # segundos
DEFAULT_MODBUS_TIMEOUT = 15  # segundos de timeout en lecturas Modbus
DEFAULT_MODBUS_RETRIES = 2  # reintentos al leer registros

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL = "serial"
CONF_INSTALLED_POWER = "installed_power"
