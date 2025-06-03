#import RPi.GPIO as GPIO
import time
from pymodbus.client.sync import ModbusSerialClient
import serial.rs485
import wiringpi
import RPiRS485
import random

RS485_DE_PIN = 17
wiringpi.wiringPiSetup()
wiringpi.pinMode(RS485_DE_PIN, wiringpi.OUTPUT)


ser=RPiRS485.RPiRS485(port='/dev/ttyAMA0',baudrate=38400,stopbits=1,timeout=1,de_pin=RS485_DE_PIN)
client = ModbusSerialClient(method='rtu')
client.socket = ser

code = random.randint(0,255)
code = code << 8
print(f"send code 0x{code:04x}")

if client.connect():
    print("✅ Connecté")
    
    response = client.write_register(0, code, unit=2)

    if response.isError():
        print("❌ Erreur :", response)
    else:
        print("✅ Réponse :", response)

    client.close()
else:
    print("❌ Erreur de connexion")

