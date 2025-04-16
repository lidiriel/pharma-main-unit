import RPi.GPIO as GPIO
import time
from pymodbus.client.sync import ModbusSerialClient

# --- Configuration RS485 ---
RS485_CONTROL_PIN = 18  # GPIO BCM 18 = broche physique 12

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)  # Mode réception par défaut

def pre_transmission():
    GPIO.output(RS485_CONTROL_PIN, GPIO.HIGH)  # Passage en émission
    time.sleep(0.001)

def post_transmission():
    time.sleep(0.001)  # Laisse le temps de finir d’émettre
    GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)   # Retour en réception

# --- Configuration du client Modbus RTU ---
client = ModbusSerialClient(
    method='rtu',
    port='/dev/ttyAMA0',
    baudrate=38400,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=1
)

# Assignation des callbacks RS485
client.pre_transmission = pre_transmission
client.post_transmission = post_transmission

# --- Connexion et envoi ---
if client.connect():
    print("✅ Connecté au port série.")
    
    # Envoi de la valeur 0xFF00 dans le registre 0 de l'esclave ID 1
    response = client.write_register(address=0, value=0xFF00, unit=1)

    if response.isError():
        print("❌ Erreur Modbus :", response)
    else:
        print("✅ Écriture réussie :", response)

    client.close()
else:
    print("❌ Impossible de se connecter au port série.")

# --- Nettoyage GPIO ---
GPIO.cleanup()
