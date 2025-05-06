## 🌞 Deye Inverter Integration for Home Assistant

This custom integration enables seamless monitoring of Deye hybrid inverters via Modbus TCP, providing real-time insights into your solar energy system directly within Home Assistant.

### ⚡ Features

- **Comprehensive Sensor Data**: Access detailed inverter metrics, including PV power, battery status, grid interaction, and more.
- **Real-Time Updates**: Leverages Modbus TCP for efficient and timely data retrieval.
- **Dynamic Entity Naming**: Automatically names entities based on inverter serial numbers for clarity.
- **Extensive Attributes**: Exposes a wide range of inverter parameters as sensor attributes.
- **Attribution Included**: Clearly indicates data source for transparency.

### 🛠️ Installation

1. **Add Repository to HACS**:
   - Navigate to HACS in Home Assistant.
   - Go to "Integrations" and click the three dots in the top right corner.
   - Select "Custom repositories" and add:
     ```
     https://github.com/jlopez77/DeyeInverterHA
     ```
     with category "Integration".

2. **Install Integration**:
   - After adding the repository, find "Deye Inverter" in the list of integrations.
   - Click "Install" and follow the prompts.

3. **Configure Integration**:
   - Once installed, go to "Configuration" > "Integrations".
   - Click "Add Integration" and select "Deye Inverter".
   - Enter your inverter's IP address and other required details.

### 📋 Notes

- Ensure your inverter is connected to your network and accessible via Modbus TCP.
- This integration is compatible with Home Assistant 2021.12.0 and above.

### 🔗 Resources

- [GitHub Repository](https://github.com/jlopez77/DeyeInverterHA)
- [Home Assistant Documentation](https://www.home-assistant.io/integrations/)

