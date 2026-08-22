"""Constantes de la integración Deye Inverter."""

DOMAIN = "deye_inverter"
DEFAULT_SCAN_INTERVAL = 30  # segundos
DEFAULT_MODBUS_TIMEOUT = 15  # segundos de timeout en lecturas Modbus
DEFAULT_MODBUS_RETRIES = 2  # reintentos al leer registros

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL = "serial"
CONF_INSTALLED_POWER = "installed_power"
CONF_MOD = "mod"

# Scaling variant of the inverter ("mod"), used as the index into the
# per-variant ratio lists in DYRealTime.txt. The protocol documentation only
# describes variant 0; the higher-power generations of the single-phase hybrid
# family report power in units of 10 W (and, from variant 2, battery current
# in 0.1 A). Naming and indices follow the community Solarman profile for the
# SG0*LP1 family so values can be cross-referenced.
MOD_VARIANTS = (0, 1, 2)
DEFAULT_MOD = 0

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
    (0x0010, 0x0012),  # rated power, MPPT and phase counts
]
# Rated power at or above this (W) means the inverter reports power in 10 W
# units, i.e. scaling variant 2. Inferred from hardware, not documented, so
# it only preselects the variant — the user always has the final say.
TEN_WATT_UNITS_FROM_RATED_POWER = 10000
REGISTER_BLOCKS = CORE_REGISTER_BLOCKS + OPTIONAL_REGISTER_BLOCKS
