import wiringpi


PINS = {
    'DE': 0,
    'ERROR': 29,
    'MSG': 28,
    'PRG':28
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
