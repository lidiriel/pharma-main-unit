import wiringpi

""" 
    Reserved GPIO
    GPIO 2    I2C SDA
    GPIO 3    I2C SCL
    GPIO 4     for shutdown
    GPIO 18    I2S Bit clock
    GPIO 19    I2S LR clock
    GPIO 20    I2S data in
    GPIO 21    I2S data out - not used -
    
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
