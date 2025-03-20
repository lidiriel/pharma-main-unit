#!python
import asyncio
from datetime import datetime
import random

import pymodbus.client as ModbusClient
from pymodbus import (
    FramerType,
    ModbusException,
    pymodbus_apply_logging_config,
)

"""
baudrate
9600
19200
38400
57600
76800
115200
"""

async def run_async_simple_client(port):
    """Run async client.
       read version register 
    """
    modbus_unit_id = 1
    register_tick = 4
    # activate debugging
    pymodbus_apply_logging_config("DEBUG")

    print("get client")
    client: ModbusClient.ModbusBaseClient
   
    client = ModbusClient.AsyncModbusSerialClient(
        port,
        # timeout=10,
        # retries=3,
        baudrate=38400,
        bytesize=8,
        parity="N",
        stopbits=1,
        # handle_local_echo=False,
    )

    print("connect to server")
    await client.connect()
    # test client is connected
    assert client.connected

    print("get and verify data")
    # try:
    #     # See all calls in client_calls.py
    #     rr = await client.read_coils(address=1, count=1, slave=1)
    # except ModbusException as exc:
    #     print(f"Received ModbusException({exc}) from library")
    #     client.close()
    #     return
    # if rr.isError():
    #     print(f"Received exception from device ({rr})")
    #     # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
    #     client.close()
    #     return
    try:
        # See all calls in client_calls.py
        # Getting the current date and time
        dt = datetime.now()

        # getting the timestamp
        #ts = int(datetime.timestamp(dt))
        #print(f"timestamp {ts}")
        ts = random.getrandbits(16)
        rr = await client.write_register(address=register_tick, value=ts, slave=modbus_unit_id)
    except ModbusException as exc:
        print(f"Received ModbusException({exc}) from library")
        client.close()
        return
    if rr.isError():
        print(f"Received exception from device ({rr})")
        # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
        client.close()
        return
    #value_int32 = client.convert_from_registers(rr.registers, data_type=client.DATATYPE.INT32)
    #print(f"Got int32: {value_int32}")
    print("close connection")
    client.close()


if __name__ == "__main__":
    # asyncio.run(
    #     run_async_simple_client("/dev/ttyUSB0"), debug=True
    # )
    import minimalmodbus
    from datetime import datetime
    import time

    instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 0)
    instrument.serial.baudrate = 38400
    instrument.serial.bytesize = 8
    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 0.2
    instrument.mode = minimalmodbus.MODE_RTU
    instrument.clear_buffers_before_each_transaction = True

    try:
        for data in [0x0000, 0x0F00, 0x0100, 0x0200, 0x0300, 0x0400, 0xFF00, 0x0000]:
            instrument.write_register(0, data)
            time.sleep(1);
    except IOError as error_msg:
        #error_msg = "Failed to read from device"
        error_time = datetime.now()
        print("IO Error Time",error_time.isoformat(),error_msg) 

    except ValueError:
        error_msg = "Failed to read CRC"
        error_time = datetime.now()
        print("Value Error Time",error_time.isoformat(),error_msg)

