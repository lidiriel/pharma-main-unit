#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os

BUTTON_GPIO = 4  # GPIO4 (pin 7)
""" Shutdown button , connectect switch to GPIO4 and GND
"""

def shutdown(channel):
    print("Shutdown button pressed")
    os.system("sudo shutdown -h now")

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING, callback=shutdown, bouncetime=2000)

try:
    print("Waiting for shutdown button press...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
