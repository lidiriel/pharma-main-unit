import wiringpi

""" GPIO 4 reserved for shutdown
"""
PINS = {
    'RS485_DE': 17,
    'HEART': 12,
}


def pinsInit():
    wiringpi.wiringPiSetup()
    for pin in PINS.values():
        wiringpi.pinMode(pin, wiringpi.OUTPUT)


def pinsWrite(pinName, v):
    if v:
        pinState = wiringpi.HIGH
    else:
        pinState = wiringpi.LOW
    wiringpi.digitalWrite(PINS[pinName], pinState)
