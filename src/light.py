import serial
import RPi.GPIO as GPIO
from time import sleep
from pymodbus.client.serial import ModbusSerialClient

# Broche GPIO pour le contrôle DE/RE du module RS485
RS485_CONTROL_PIN = 18  # GPIO18 correspond à la broche physique 12

# Configuration GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)  # Commence en réception



class RS485ModbusClient(ModbusSerialClient):
    def __init__(self, *args, rs485_pin=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rs485_pin = rs485_pin
        if rs485_pin is not None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(rs485_pin, GPIO.OUT)
            GPIO.output(rs485_pin, GPIO.LOW)  # Commencer en réception

    def _send(self, request):
        # Passage en émission
        if self.rs485_pin is not None:
            GPIO.output(self.rs485_pin, GPIO.HIGH)
            sleep(0.001)

        result = super()._send(request)

        # Retour en réception
        if self.rs485_pin is not None:
            sleep(0.001)
            GPIO.output(self.rs485_pin, GPIO.LOW)

        return result


# Création du client Modbus
client = RS485ModbusClient(
    port='/dev/ttyAMA0',
    baudrate=38400,
    timeout=1,
    stopbits=1,
    bytesize=8,
    parity='N'
)

# Connexion
if not client.connect():
    print("Erreur de connexion au bus Modbus.")
    exit(1)


# Envoi de la valeur
slave_id = 1
register_address = 0
value = 0xFF00

response = client.write_register(register_address, value, slave=slave_id)

if response.isError():
    print("Erreur lors de l'écriture Modbus :", response)
else:
    print("Écriture réussie :", response)

# Nettoyage
client.close()
GPIO.cleanup()
