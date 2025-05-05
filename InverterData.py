import binascii
import json
import os
import socket


def twos_complement_hex(hexval: str) -> int:
    """Interpreta un valor hex como entero con complemento a dos (16 bits)."""
    bits = 16
    val = int(hexval, 16)
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val


def crc16_modbus(data: bytes) -> int:
    """Calcula el CRC-16 Modbus de un bloque de bytes."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class InverterData:
    """Clase para leer datos en tiempo real de un inversor Deye vía Modbus/TCP."""

    def __init__(self, host: str, port: int, serial: str, installed_power: int):
        """
        Recibe los parámetros desde Home Assistant:
        - host: IP o hostname del inversor
        - port: puerto Modbus/TCP
        - serial: número de serie (string o int)
        - installed_power: potencia instalada, para cálculo si es necesario
        """
        self.host = host
        self.port = port
        self.serial = int(serial, 0) if isinstance(serial, str) else int(serial)
        self.installed_power = installed_power
        # Ruta al fichero de definición de registros
        self._params_file = os.path.join(os.path.dirname(__file__), "DYRealTime.txt")

    def read_real_time(self) -> dict[int, float]:
        """
        Consulta dos bloques de registros al inversor y devuelve
        un diccionario {registro_modbus_int: valor_transformado}.
        """
        data_map: dict[int, float] = {}

        # Carga la definición de parámetros desde el JSON
        with open(self._params_file, "r", encoding="utf-8") as f:
            parameters = json.load(f)

        # Se consultan dos rangos de registros (bloques)
        for pini, pfin in [(59, 112), (150, 195)]:
            count = pfin - pini + 1

            # Construcción de la trama de consulta
            start = binascii.unhexlify("A5")
            length = binascii.unhexlify("1700")
            controlcode = binascii.unhexlify("1045")
            serial_bytes = binascii.unhexlify("0000")
            datafield = binascii.unhexlify("020000000000000000000000000000")
            businessfield = binascii.unhexlify(f"0103{pini:04x}{count:04x}")
            crc_bytes = crc16_modbus(businessfield).to_bytes(2, byteorder="little")
            checksum = binascii.unhexlify("00")
            endcode = binascii.unhexlify("15")

            # Serial del inversor en 4 bytes little-endian
            inv_sn_hex = f"{self.serial:08x}"
            inverter_sn2 = bytearray.fromhex(
                inv_sn_hex[6:8] + inv_sn_hex[4:6] + inv_sn_hex[2:4] + inv_sn_hex[0:2]
            )

            frame = bytearray(
                start
                + length
                + controlcode
                + serial_bytes
                + inverter_sn2
                + datafield
                + businessfield
                + crc_bytes
                + checksum
                + endcode
            )

            # Recalcula el checksum sencillo (byte antes del endcode)
            simple_checksum = sum(frame[i] for i in range(1, len(frame) - 2)) & 0xFF
            frame[-2] = simple_checksum

            # Envío de la trama y recepción de la respuesta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                sock.sendall(frame)
                data = sock.recv(1024)

            # Convierte la respuesta a cadena hex continua
            raw_hex = "".join(f"{b:02x}" for b in data)

            # Parseo de cada registro de 2 bytes (4 hex chars)
            for offset in range(count):
                p1 = 56 + offset * 4
                p2 = p1 + 4
                segment = raw_hex[p1:p2]
                value = twos_complement_hex(segment)

                # Dirección modbus en formato "0x00BA" (0x minúscula, dígitos en mayúscula)
                hexpos = f"0x{pini + offset:04X}"

                # Busca en la definición de parámetros y aplica ratio/offset
                for group in parameters:
                    for item in group["items"]:
                        if hexpos in item["registers"]:
                            title = item["titleEN"]
                            ratio = item.get("ratio", 1)
                            if "Temperature" in title:
                                val = round(value * ratio - 100, 2)
                            else:
                                val = round(value * ratio, 2)
                            data_map[int(hexpos, 16)] = val
                            break

        return data_map
