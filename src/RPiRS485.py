import serial
import wiringpi
import array
import fcntl
import termios


class RPiRS485(serial.Serial):
    def __init__(self, de_pin=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buf = array.array('h', [0])
        self.de_pin = de_pin
        

    def write(self, b):
        wiringpi.digitalWrite(self.de_pin, wiringpi.HIGH)
        super().write(b)
        while True:
            fcntl.ioctl(self.fileno(), termios.TIOCSERGETLSR, self.buf, 1)
            if self.buf[0] & termios.TIOCSER_TEMT:
                break
        wiringpi.digitalWrite(self.de_pin, wiringpi.LOW)
