import serial
import RPi.GPIO as GPIO
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
from time import sleep

# Broche GPIO pour le contrôle DE/RE du module RS485
RS485_CONTROL_PIN = 18  # GPIO18 correspond à la broche physique 12

# Configuration GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)  # Commence en réception

# Fonction pour contrôler l'interface RS485
def pre_transmission():
    GPIO.output(RS485_CONTROL_PIN, GPIO.HIGH)  # Passage en émission
    sleep(0.001)

def post_transmission():
    sleep(0.001)
    GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)   # Retour en réception

# Création du client Modbus
client = ModbusClient(
    method='rtu',
    port='/dev/ttyAMA0',  # Interface UART du Raspberry Pi
    baudrate=9600,
    timeout=1,
    stopbits=1,
    bytesize=8,
    parity='N'
)

# Connexion au bus
if not client.connect():
    print("Erreur de connexion au bus Modbus.")
    exit(1)

# Affectation des callbacks pour le contrôle RS485
client.pre_transmission = pre_transmission
client.post_transmission = post_transmission

# Envoi de la valeur 0xFF00 dans le registre 0 de l'esclave 1
slave_id = 0
register_address = 0
value = 0xFF00

response = client.write_register(register_address, value, unit=slave_id)

if response.isError():
    print("Erreur lors de l'écriture Modbus :", response)
else:
    print("Écriture réussie :", response)

# Nettoyage
client.close()
GPIO.cleanup()
