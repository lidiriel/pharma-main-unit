import RPi.GPIO as GPIO
import time

# Choisir le mode BCM ou BOARD
GPIO.setmode(GPIO.BCM)  # Utilise les numéros GPIO (ex: GPIO12)
# GPIO.setmode(GPIO.BOARD)  # Utilise les numéros de pin physique (ex: pin 32)

PIN_LED = 12  # GPIO12 (BCM) ou pin 32 (BOARD)

GPIO.setup(PIN_LED, GPIO.OUT)

print("Test LED clignotante. Ctrl+C pour arrêter.")
try:
    while True:
        GPIO.output(PIN_LED, GPIO.HIGH)
        print("LED ON")
        time.sleep(1)
        GPIO.output(PIN_LED, GPIO.LOW)
        print("LED OFF")
        time.sleep(1)
except KeyboardInterrupt:
    print("Arrêté par l'utilisateur.")
finally:
    GPIO.cleanup()
