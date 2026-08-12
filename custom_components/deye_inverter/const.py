"""Constantes de la integración Deye Inverter."""

DOMAIN = "deye_inverter"
DEFAULT_SCAN_INTERVAL = 30  # segundos
DEFAULT_MODBUS_TIMEOUT = 15  # segundos de timeout en lecturas Modbus
DEFAULT_MODBUS_RETRIES = 2  # reintentos al leer registros

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL = "serial"
CONF_INSTALLED_POWER = "installed_power"

# Holding-register blocks read on every update, as (first, last) inclusive.
# Core blocks must succeed or the whole read fails; optional blocks are read
# best-effort (some devices may not expose them). Order defines the layout of
# the flat register list passed to the parser, so only append new blocks.
CORE_REGISTER_BLOCKS = [
    (0x003B, 0x0070),  # daily/total counters, temperatures, alerts
    (0x0096, 0x00C3),  # grid, battery, load, PV real-time values
]
OPTIONAL_REGISTER_BLOCKS = [
    (0x0003, 0x000E),  # device info: inverter id, board versions
    (0x00F4, 0x00F8),  # work mode, time of use
]
REGISTER_BLOCKS = CORE_REGISTER_BLOCKS + OPTIONAL_REGISTER_BLOCKS
