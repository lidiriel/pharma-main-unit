#!python
import asyncio
from datetime import datetime
import random


"""
baudrate
9600
19200
38400
57600
76800
115200
"""

if __name__ == "__main__":
    import minimalmodbus
    from datetime import datetime
    import time

    instrument = minimalmodbus.Instrument(port='/dev/ttyAMA0', slaveaddress=0)
    instrument.serial.baudrate = 76800
    instrument.serial.bytesize = 8
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 0
    instrument.mode = minimalmodbus.MODE_RTU
    instrument.clear_buffers_before_each_transaction = True

    try:
        for data in [0x0101, 0x0202, 0x0404, 0x0808, 0x1010, 0x2020, 0x4040, 0x8080, 0x0000]:
            print(f"send {data:04x}")
            instrument.write_register(0, data)
            time.sleep(2);
    except IOError as error_msg:
        #error_msg = "Failed to read from device"
        error_time = datetime.now()
        print("IO Error Time",error_time.isoformat(),error_msg) 

    except ValueError:
        error_msg = "Failed to read CRC"
        error_time = datetime.now()
        print("Value Error Time",error_time.isoformat(),error_msg)

