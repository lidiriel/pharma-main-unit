import RPi.GPIO as GPIO
import time
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.transaction import ModbusRtuFramer

RS485_CONTROL_PIN = 18

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)

def pre_transmission():
    print("[GPIO] → Émission")
    GPIO.output(RS485_CONTROL_PIN, GPIO.HIGH)
    time.sleep(0.001)

def post_transmission():
    time.sleep(0.001)
    GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)
    print("[GPIO] → Réception")

client = ModbusSerialClient(
    method='rtu',
    port='/dev/ttyAMA0',
    baudrate=38400,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=1,
    framer=ModbusRtuFramer
)

client.pre_transmission = pre_transmission
client.post_transmission = post_transmission

if client.connect():
    print("✅ Connecté")

    response = client.write_register(0, 0xFF00, unit=2)

    if response.isError():
        print("❌ Erreur :", response)
    else:
        print("✅ Réponse :", response)

    client.close()
else:
    print("❌ Erreur de connexion")

GPIO.cleanup()
