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

In the UI, go to Settings > Devices & Services > Add Integration, search for Deye Inverter, and follow the setup steps.
