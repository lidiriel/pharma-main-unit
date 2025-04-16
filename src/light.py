#import RPi.GPIO as GPIO
import time
from pymodbus.client.sync import ModbusSerialClient
import serial.rs485
import wiringpi
import RPiRS485

RS485_CONTROL_PIN = 17

#GPIO.setwarnings(False)
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
#GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)
wiringpi.wiringPiSetup()
wiringpi.pinMode(RS485_CONTROL_PIN, wiringpi.OUTPUT)


ser=RPiRS485.RPiRS485(port='/dev/ttyAMA0',baudrate=38400,stopbits=1,timeout=0.1)
client = ModbusSerialClient(method='rtu')
client.socket = ser


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

#GPIO.cleanup()
