# Deye Inverter Integration for Home Assistant

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Quality: Silver](https://img.shields.io/badge/Quality-Silver-silver)
![Tests](https://github.com/jlopez77/DeyeInverterHA/actions/workflows/python-app.yml/badge.svg)
![Coverage](https://codecov.io/gh/jlopez77/DeyeInverterHA/branch/main/graph/badge.svg)

## Overview

This custom integration allows Home Assistant to read **real-time data** from **Deye hybrid inverters** over Modbus TCP, using a mapping file based on `DYRealTime.txt` and powered by [`PySolarmanV5`](https://github.com/jlopez77/pysolarmanv5) and `pymodbus`.

It creates **one sensor entity per inverter metric** (40+ entities), all grouped under a single inverter device, with proper device classes and state classes — so energy metrics work with the **Energy dashboard** and get long-term statistics.

---

## Features

- 📡 Real-time data from Deye hybrid inverters
- 🧠 Based on `PySolarmanV5` and `pymodbus`
- 🧩 UI-based configuration (no YAML needed)
- 📊 One entity per metric (40+ sensors) with device/state classes and statistics
- ⚡ Energy dashboard support (kWh sensors with `total_increasing`)
- 💡 Works offline — no cloud dependency

---

## Installation

This integration is **not yet in HACS**. You can install it manually for now:

### Requirements

- Home Assistant 2021.12 or newer
- Network access to your inverter's Modbus TCP interface

### Manual Steps

1. Download or clone this repository:

   ```bash
   git clone https://github.com/jlopez77/DeyeInverterHA.git
   ```

2. Copy the folder `custom_components/deye_inverter` into your Home Assistant config directory:

   ```
   config/custom_components/deye_inverter
   ```

3. Restart Home Assistant.

4. In the UI, go to Settings > Devices & Services > Add Integration, search for Deye Inverter, and follow the setup steps.

## Configuration
Once installed, the integration can be configured entirely through the Home Assistant UI.

You will be asked for:

- Host: The IP address of your inverter
- Port: Modbus TCP port (default: 8899)
- Serial Number: The datalogger’s serial number (something like 17XXXXXX)
- Installed Power (kW): Used for the *Production* (%) sensor

The connection is tested before the entry is created — if the inverter is not
reachable (wrong host/port/serial, or another client is holding the datalogger's
single TCP slot) the form shows an error instead of creating a broken entry.

## Entities

All entities are grouped under one **Deye Inverter** device.

### Aggregate Sensor
`sensor.deye_inverter` — total inverter PV production (PV1 + PV2), kept for backward compatibility.

### Production Sensor
*Production* — current PV output as a percentage of the installed power you configured (e.g. 800 W of 5 kW → 16 %).

> **Breaking change:** this sensor no longer exposes the inverter metrics as
> `extra_state_attributes`. Templates reading attributes from it must switch to
> the dedicated per-metric sensors below. Status values are now plain strings
> (e.g. `Discharge` instead of `Discharge (12)`) and Total Grid Production is
> numeric.

### Per-Metric Sensors
One sensor per metric, named after the metric (e.g. *PV1 Power*, *Battery SOC*, *Total Grid Production*). Units, device classes, and state classes are derived automatically, so:

- Power/voltage/current/temperature sensors record statistics (`measurement`)
- Energy sensors (kWh) use `total_increasing` and can be used in the **Energy dashboard**
- Status sensors (Battery Status, Grid Status, Running Status, Alert, …) are text sensors in the *Diagnostic* category

Available metrics:

- PV: PV1/PV2 Voltage, Current, Power; Daily/Total Production; Micro-inverter Power
- Battery: Voltage, Current, Power, SOC, Temperature, Status
- Grid: Grid Voltage L1/L2, Grid Status, Grid-connected Status, Total Grid Power, Total Grid Production, Daily/Total Energy Bought and Sold, Internal/External CT L1/L2 Power
- Load: Load L1/L2 Power, Load Voltage, Total Load Power, Daily/Total Load Consumption, SmartLoad Enable Status
- Inverter: Running Status, Total Power, Current L1/L2, Inverter L1/L2 Power, AC/DC Temperature, Gen Power, Gen-connected Status
- Alert (bitfield, hex string)

## Troubleshooting

🔌 No data / Sensor unavailable:

Check inverter IP and port (default is usually 8899)
Verify that the inverter is online and responding to Modbus TCP
Check if the serial number is correct

⚙️ Integration not showing up:

Make sure files are correctly placed under `config/custom_components/deye_inverter`

Restart Home Assistant

## Contributing
This integration is under active development and contributions are welcome. If you encounter issues or have suggestions:

Open an issue

Submit a pull request with improvements or fixes

## License
This project is licensed under the MIT License. See the LICENSE file for details.
