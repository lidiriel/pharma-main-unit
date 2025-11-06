#!/usr/bin/env python3
import lgpio
import time
import os

BUTTON_GPIO = 4  # GPIO4 (pin 7)
""" Shutdown button , connectect switch to GPIO4 and GND
"""

def shutdown(channel):
    print("Shutdown button pressed")
    os.system("sudo shutdown -h now")

handler = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(handler, BUTTON_GPIO)

lgpio.callback(0, BUTTON_GPIO, lgpio.BOTH_EDGES, shutdown)

try:
    print("Waiting for shutdown button press...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
lgpio.gpiochip_close(handler)
