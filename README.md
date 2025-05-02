# Deye Inverter – Integración para Home Assistant

📢 **Aviso**: Esta integración aún está en desarrollo y cumple el nivel **Bronze** de la Home Assistant Quality Scale. ¡Tu feedback es bienvenido!

## Descripción

El componente **Deye Inverter** te permite leer en tiempo real los datos de inversores Deye vía Modbus/TCP y exponerlos en Home Assistant como un único sensor de potencia principal (`sensor.deye_inverter_power`) con **todos** los demás valores (voltajes, corrientes, energía, estado, etc.) en sus atributos.

- Estado principal: **Total PV Power** (PV1 + PV2).  
- Atributos: estado de batería, potencia de red, consumos, temperaturas, alarmas…  
- Compatible con UI config flow: configura host, puerto, número de serie y potencia instalada.  
- Soporta modos claro/oscuro: `icon.png`/`dark_icon.png` y `logo.png`/`dark_logo.png`.  

---

## Características

- ✅ Configuración 100 % desde UI (no requiere YAML).  
- ✅ Sensor principal con icono MDI (`mdi:solar-power`).  
- ✅ Atributos ricos con todos los registros de DYRealTime.txt.  
- ✅ Reintento silencioso si pierde conexión (mantiene últimos datos).  
- ✅ Integración con Energy Dashboard gracias a `device_class` y `state_class`.  

---

## Requisitos

- Home Assistant ≥ 2025.2  
- Sólo dependencias internas. No requiere `configuration.yaml` extra (salvo `logger` si quieres ver debug).  

---

## Instalación

1. Copia la carpeta `custom_components/deye_inverter/` en tu directorio `<config>/custom_components/`.  
2. Reinicia Home Assistant.  
3. Ve a **Ajustes → Integraciones → Añadir integración** y busca **Deye Inverter**.  
4. Introduce:
   - **Host**: IP o hostname del inversor.  
   - **Port**: Puerto Modbus/TCP (p.ej. 502).  
   - **Serial**: Número de serie de 8 hex-dígitos.  
   - **Installed power**: Potencia instalada (en W).  

---

## Entidades

| Entity ID                        | Descripción                 | Unidad | Device class | State class           |
| -------------------------------- | --------------------------- | ------ | ------------ | --------------------- |
| `sensor.deye_inverter_power`     | **Total PV Power**          | W      | power        | measurement           |
| *(atributos)*                    | _Todos los demás valores_*  | —      | —            | —                     |

> Todos los demás registros —voltajes, corrientes, energías, estados, temperatura— están en `extra_state_attributes` de `sensor.deye_inverter_power`, accesibles como:
> ```jinja
> state_attr('sensor.deye_inverter_power', 'Battery Voltage')
> state_attr('sensor.deye_inverter_power', 'Grid Voltage L1')
> state_attr('sensor.deye_inverter_power', 'Daily Energy Bought')
> # etc.
> ```

---

## Ejemplos de uso

### Dashboard Lovelace

```yaml
type: entities
title: Deye Inverter Overview
show_header_toggle: false
entities:
  - entity: sensor.deye_inverter_power
    name: Potencia Solar Total
  - attribute: “Battery SOC”
    entity: sensor.deye_inverter_power
    name: Estado de Carga (%)
  - attribute: “Grid Status”
    entity: sensor.deye_inverter_power
    name: Estado de Red
  - attribute: “Battery Power”
    entity: sensor.deye_inverter_power
    name: Potencia Batería
  - attribute: “DC Temperature”
    entity: sensor.deye_inverter_power
    name: Temp. DC (ºC)
