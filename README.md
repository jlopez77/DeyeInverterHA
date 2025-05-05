# Deye Inverter Integration for Home Assistant

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Quality: Silver](https://img.shields.io/badge/Quality-Silver-silver)

## Overview

This custom integration allows Home Assistant to read **real-time data** from **Deye hybrid inverters** over Modbus TCP, using a mapping file based on `DYRealTime.txt` and powered by [`PySolarmanV5`](https://github.com/jlopez77/pysolarmanv5) and `pymodbus`.

It provides a single sensor entity — **`sensor.deye_inverter`** — with a wide set of inverter metrics exposed via `extra_state_attributes`.

---

## Features

- 📡 Real-time data from Deye hybrid inverters
- 🧠 Based on `PySolarmanV5` and `pymodbus`
- 🧩 UI-based configuration (no YAML needed)
- 📊 Exposes 50+ inverter metrics as sensor attributes
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

2. Copy the folder:

   ```bash
   custom_components/deyeinverter

  into your Home Assistant config directory:

   ```bash
   config/custom_components/deyeinverter
```
3. Restart Home Assistant.

4. In the UI, go to Settings > Devices & Services > Add Integration, search for Deye Inverter, and follow the setup steps.

## Configuration
Once installed, the integration can be configured entirely through the Home Assistant UI.

You will be asked for:

Host: The IP address of your inverter
Port: Modbus TCP port (default: 8899)
Serial Number: The inverter’s serial number
Installed Power (kW): For production % estimation

## Entities
### Main Sensor
sensor.deye_inverter
Represents total inverter PV production (PV1 + PV2). This sensor includes all inverter metrics as attributes.

## Available Attributes
### The sensor exposes all of the following as extra_state_attributes:

PV Metrics
PV1 Voltage
PV1 Current
PV1 Power
PV2 Voltage
PV2 Current
PV2 Power
Battery
Battery Voltage
Battery Current
Battery Power
Battery SOC
Battery Temperature
Battery Status
Grid
Grid Voltage L1
Grid Voltage L2
Grid-connected Status
Total Grid Power
Total Grid Production
Total Energy Bought
Total Energy Sold
Daily Energy Bought
Daily Energy Sold
Load
Load L1 Power
Load L2 Power
Load Voltage
Total Load Power
Total Load Consumption
Daily Load Consumption
Temperature
AC Temperature
DC Temperature
Other Metrics
Total Production
Daily Production
Total Power
Time of use
SmartLoad Enable Status
Gen-connected Status
Gen Power
Running Status
Alert
Work Mode
Inverter ID
Inverter L1 Power
Inverter L2 Power
Communication Board Version No.
Control Board Version No.
Micro-inverter Power
External CT L1 Power
External CT L2 Power
Internal CT L1 Power
Internal CT L2 Power

## Troubleshooting

🔌 No data / Sensor unavailable:

Check inverter IP and port (default is usually 8899)
Verify that the inverter is online and responding to Modbus TCP
Check if the serial number is correct

⚙️ Integration not showing up:

Make sure files are correctly placed under config/custom_components/deyeinverter

Restart Home Assistant

## Contributing
This integration is under active development and contributions are welcome. If you encounter issues or have suggestions:

Open an issue

Submit a pull request with improvements or fixes

## License
This project is licensed under the MIT License. See the LICENSE file for details.
