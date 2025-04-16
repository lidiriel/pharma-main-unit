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

# Fonctions pour contrôle de direction RS485
def pre_transmission():
    GPIO.output(RS485_CONTROL_PIN, GPIO.HIGH)
    sleep(0.001)

def post_transmission():
    sleep(0.001)
    GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)

# Création du client Modbus (sans le paramètre 'method')
client = ModbusClient(
    port='/dev/ttyAMA0',
    baudrate=9600,
    timeout=1,
    stopbits=1,
    bytesize=8,
    parity='N'
)

# Connexion
if not client.connect():
    print("Erreur de connexion au bus Modbus.")
    exit(1)

# Ajout des callbacks
client.pre_transmission = pre_transmission
client.post_transmission = post_transmission

# Envoi de la valeur
slave_id = 1
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
