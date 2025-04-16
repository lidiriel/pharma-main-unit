import asyncio
import RPi.GPIO as GPIO
from pymodbus.client import ModbusSerialClient
from pymodbus.transport.serial import SerialTransport
from serial_asyncio import create_serial_connection
from pymodbus.transaction import ModbusRtuFramer

RS485_CONTROL_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(RS485_CONTROL_PIN, GPIO.OUT)
GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)  # réception

class RS485SerialTransport(SerialTransport):
    async def _send(self, request):
        # Active émission
        GPIO.output(RS485_CONTROL_PIN, GPIO.HIGH)
        await asyncio.sleep(0.001)

        await super()._send(request)

        await asyncio.sleep(0.001)  # temps pour vider le buffer TX
        # Rebasculer en réception avant la réponse
        GPIO.output(RS485_CONTROL_PIN, GPIO.LOW)

async def main():
    client = ModbusSerialClient(
        port='/dev/ttyAMA0',
        baudrate=38400,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=1,
        framer=ModbusRtuFramer,
        transport=RS485SerialTransport
    )

    await client.connect()
    if not client.connected:
        print("Erreur de connexion")
        return

    result = await client.write_register(0, 0xFF00, unit=2)
    if result.isError():
        print("Erreur Modbus :", result)
    else:
        print("Succès :", result)

    await client.close()
    GPIO.cleanup()

# Lancer la boucle asyncio
asyncio.run(main())
